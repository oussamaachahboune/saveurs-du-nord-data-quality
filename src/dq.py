"""Fonctions partagées de l'audit qualité — Les Saveurs du Nord.

Le module se limite à la détection : aucune fonction ne modifie les données.
Les règles sont décrites dans rules/rules_catalog.csv ; chaque rule_id y est
associé à une fonction de contrôle enregistrée ici avec le décorateur @rule.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RULES_DIR = PROJECT_ROOT / "rules"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Fichier source -> colonne identifiant
ID_COLUMNS = {"clients.csv": "id_client", "produits.csv": "id_produit"}

ALLOWED_VAT_RATES = [2.1, 5.5, 10.0, 20.0]
LOW_STOCK_THRESHOLD = 20  # hypothèse documentée dans PRD-COH-02


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------

def load_raw(file_name: str) -> pd.DataFrame:
    """Charge un CSV brut sans aucune conversion : tout reste en texte."""
    path = RAW_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} introuvable : placer les CSV bruts dans data/raw/ (voir README)."
        )
    return pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )


def load_datasets() -> dict[str, pd.DataFrame]:
    return {file_name: load_raw(file_name) for file_name in ID_COLUMNS}


def file_fingerprint(file_name: str) -> dict:
    """Empreinte SHA-256 du fichier brut : sert de version du fichier analysé."""
    path = RAW_DIR / file_name
    return {
        "file": file_name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def load_rules_catalog() -> pd.DataFrame:
    return pd.read_csv(
        RULES_DIR / "rules_catalog.csv",
        sep=";",
        encoding="utf-8",
        dtype=str,
        keep_default_na=False,
    )


def load_city_reference() -> pd.DataFrame:
    return pd.read_csv(
        RULES_DIR / "ref_villes_cp.csv",
        sep=";",
        encoding="utf-8",
        dtype=str,
        keep_default_na=False,
    )


# ---------------------------------------------------------------------------
# Outils de base
# ---------------------------------------------------------------------------

def is_blank(series: pd.Series) -> pd.Series:
    """NULL, chaîne vide ou chaîne composée uniquement d'espaces."""
    return series.isna() | series.str.strip().eq("")


def to_number(series: pd.Series) -> pd.Series:
    """Conversion numérique sans modifier la série d'origine (NaN si impossible)."""
    return pd.to_numeric(series.where(~is_blank(series)).str.strip(), errors="coerce")


def tukey_bounds(values: pd.Series, k: float = 1.5) -> tuple[float, float]:
    """Bornes de Tukey : [Q1 - k x IQR, Q3 + k x IQR]."""
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Complétude par colonne en distinguant NULL, vide et espaces seuls."""
    rows = len(df)
    summary = pd.DataFrame({
        "null_count": df.isna().sum(),
        "empty_string_count": df.eq("").sum(),
        "whitespace_only_count": df.apply(
            lambda column: column.str.fullmatch(r"\s+", na=False).sum()
        ),
        "surrounding_spaces_count": df.apply(
            lambda column: (column.notna() & column.ne(column.str.strip())).sum()
        ),
    })
    summary["populated_count"] = rows - df.apply(is_blank).sum()
    summary["completeness_pct"] = (summary["populated_count"] / rows * 100).round(1)
    return summary


def _normalized(series: pd.Series) -> pd.Series:
    return series.str.strip().str.lower()


# ---------------------------------------------------------------------------
# Registre des règles
# Chaque fonction reçoit (df, fields, ctx) et renvoie :
#   - une Series booléenne (True = ligne en violation), ou
#   - un DataFrame booléen avec une colonne par champ contrôlé.
# ---------------------------------------------------------------------------

RULES: dict[str, callable] = {}


def rule(*rule_ids: str):
    def register(function):
        for rule_id in rule_ids:
            RULES[rule_id] = function
        return function
    return register


@rule("CLI-INT-01", "PRD-INT-01")
def check_id_populated(df, fields, ctx):
    return is_blank(df[fields[0]])


@rule("CLI-INT-02", "PRD-INT-02")
def check_id_unique(df, fields, ctx):
    identifiers = df[fields[0]]
    return ~is_blank(identifiers) & identifiers.duplicated(keep=False)


@rule("CLI-INT-03", "PRD-INT-03")
def check_full_row_duplicates(df, fields, ctx):
    return df.duplicated(keep=False)


@rule("CLI-COM-01", "CLI-COM-02", "PRD-COM-01")
def check_populated(df, fields, ctx):
    return pd.DataFrame({field: is_blank(df[field]) for field in fields})


@rule("CLI-VAL-01")
def check_email_format(df, fields, ctx):
    email = df["email"]
    valid = email.str.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", na=False)
    return ~is_blank(email) & ~valid


@rule("CLI-VAL-02")
def check_phone_format(df, fields, ctx):
    phone = df["telephone"]
    digits = phone.str.replace(r"[\s.\-]", "", regex=True)
    valid = digits.str.fullmatch(r"(?:0[1-9][0-9]{8}|\+33[1-9][0-9]{8})", na=False)
    return ~is_blank(phone) & ~valid


@rule("CLI-VAL-03")
def check_date_format(df, fields, ctx):
    raw = df["date_inscription"]
    parsed = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    valid = raw.str.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", na=False) & parsed.notna()
    return ~is_blank(raw) & ~valid


@rule("CLI-VAL-04")
def check_age_range(df, fields, ctx):
    age = to_number(df["age"])
    invalid = age.isna() | age.mod(1).ne(0) | age.lt(0) | age.gt(120)
    return ~is_blank(df["age"]) & invalid


@rule("CLI-VAL-05")
def check_adult(df, fields, ctx):
    age = to_number(df["age"])
    return age.notna() & age.lt(18)


@rule("CLI-VAL-06")
def check_postal_code_format(df, fields, ctx):
    postal_code = df["code_postal"]
    valid = postal_code.str.fullmatch(r"[0-9]{5}", na=False)
    return ~is_blank(postal_code) & ~valid


@rule("CLI-VAL-07")
def check_client_type(df, fields, ctx):
    client_type = df["type_client"]
    return ~is_blank(client_type) & ~client_type.isin(["Particulier", "Professionnel"])


@rule("CLI-COH-01")
def check_city_postal_code(df, fields, ctx):
    reference = ctx["city_reference"]
    known_city = df["ville"].isin(reference["ville"])
    pairs = df["ville"] + "|" + df["code_postal"]
    known_pair = pairs.isin(reference["ville"] + "|" + reference["code_postal"])
    return ~is_blank(df["code_postal"]) & known_city & ~known_pair


@rule("CLI-COH-02")
def check_date_not_future(df, fields, ctx):
    parsed = pd.to_datetime(df["date_inscription"], format="%Y-%m-%d", errors="coerce")
    return parsed.notna() & parsed.gt(pd.Timestamp(ctx["run_date"]))


@rule("CLI-UNI-01")
def check_email_unique(df, fields, ctx):
    email = df["email"]
    return ~is_blank(email) & _normalized(email).duplicated(keep=False)


@rule("CLI-UNI-02", "PRD-UNI-01")
def check_attribute_pair_unique(df, fields, ctx):
    key = _normalized(df[fields[0]]) + "|" + _normalized(df[fields[1]])
    return key.duplicated(keep=False)


@rule("CLI-OUT-01", "PRD-OUT-01", "PRD-OUT-02")
def check_tukey_outliers(df, fields, ctx):
    values = to_number(df[fields[0]])
    low, high = tukey_bounds(values.dropna())
    return values.notna() & (values.lt(low) | values.gt(high))


@rule("PRD-VAL-01")
def check_price(df, fields, ctx):
    price = to_number(df["prix_unitaire_eur"])
    return ~is_blank(df["prix_unitaire_eur"]) & (price.isna() | price.lt(0))


@rule("PRD-VAL-02")
def check_vat_rate(df, fields, ctx):
    rate = to_number(df["tva_pct"])
    return ~is_blank(df["tva_pct"]) & ~rate.isin(ALLOWED_VAT_RATES)


@rule("PRD-VAL-03")
def check_stock(df, fields, ctx):
    stock = to_number(df["stock_unites"])
    invalid = stock.isna() | stock.lt(0) | stock.mod(1).ne(0)
    return ~is_blank(df["stock_unites"]) & invalid


@rule("PRD-VAL-04")
def check_stock_status(df, fields, ctx):
    status = df["statut_stock"]
    return ~is_blank(status) & ~status.isin(["En stock", "Stock faible"])


@rule("PRD-COH-01")
def check_no_stock_available(df, fields, ctx):
    stock = to_number(df["stock_unites"])
    available = df["statut_stock"].isin(["En stock", "Stock faible"])
    return stock.notna() & stock.le(0) & available


@rule("PRD-COH-02")
def check_low_stock_threshold(df, fields, ctx):
    stock = to_number(df["stock_unites"])
    status = df["statut_stock"]
    in_domain = status.isin(["En stock", "Stock faible"])
    expected_low = stock.lt(ctx["low_stock_threshold"])
    declared_low = status.eq("Stock faible")
    return stock.notna() & stock.gt(0) & in_domain & expected_low.ne(declared_low)


@rule("PRD-EXA-01")
def check_alcohol_free_vat(df, fields, ctx):
    rate = to_number(df["tva_pct"])
    alcohol_free = df["nom_produit"].str.contains("sans alcool", case=False, na=False)
    return alcohol_free & rate.eq(20)


@rule("PRD-EXA-02")
def check_gift_card_vat(df, fields, ctx):
    rate = to_number(df["tva_pct"])
    return df["categorie"].eq("Cartes cadeaux") & rate.gt(0)


# ---------------------------------------------------------------------------
# Exécution des règles
# ---------------------------------------------------------------------------

def default_context(run_date: date | None = None) -> dict:
    return {
        "run_date": run_date or date.today(),
        "city_reference": load_city_reference(),
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
    }


def check_catalog_consistency(catalog: pd.DataFrame) -> None:
    """Vérifie que chaque règle du catalogue est implémentée, et inversement."""
    missing = set(catalog["rule_id"]) - set(RULES)
    extra = set(RULES) - set(catalog["rule_id"])
    if missing or extra:
        raise ValueError(f"Règles non implémentées : {missing} ; hors catalogue : {extra}")


def _observed_value(df: pd.DataFrame, position: int, fields: list[str]) -> str:
    if fields == ["all_columns"]:
        return "(ligne complète)"
    if len(fields) == 1:
        return repr(df[fields[0]].iloc[position])
    return " | ".join(f"{field}={df[field].iloc[position]!r}" for field in fields)


def run_rules(
    datasets: dict[str, pd.DataFrame],
    catalog: pd.DataFrame | None = None,
    ctx: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applique toutes les règles du catalogue.

    Renvoie :
    - results : une ligne par règle (lignes testées, lignes en violation, taux) ;
    - violations : une ligne par (enregistrement, champ, règle) en violation.
    Le numéro de ligne commence à 1, sans compter l'en-tête du CSV.
    """
    catalog = load_rules_catalog() if catalog is None else catalog
    ctx = default_context() if ctx is None else ctx
    check_catalog_consistency(catalog)

    results, violations = [], []

    for spec in catalog.itertuples(index=False):
        df = datasets[spec.file]
        id_column = ID_COLUMNS[spec.file]
        fields = spec.field.split("|")
        outcome = RULES[spec.rule_id](df, fields, ctx)

        if isinstance(outcome, pd.DataFrame):
            masks = {field: outcome[field] for field in outcome.columns}
            row_mask = outcome.any(axis=1)
        else:
            masks = {spec.field: outcome}
            row_mask = outcome

        for field, mask in masks.items():
            reported_fields = field.split("|")
            for position in mask.to_numpy().nonzero()[0]:
                violations.append({
                    "rule_id": spec.rule_id,
                    "file": spec.file,
                    "row_number": position + 1,
                    "identifier": df[id_column].iloc[position],
                    "dimension": spec.dimension,
                    "field": field,
                    "rule": spec.rule,
                    "observed_value": _observed_value(df, position, reported_fields),
                    "test_result": spec.result_if_violated,
                })

        rows_violating = int(row_mask.sum())
        results.append({
            "rule_id": spec.rule_id,
            "file": spec.file,
            "dimension": spec.dimension,
            "field": spec.field,
            "rule": spec.rule,
            "rows_tested": len(df),
            "rows_violating": rows_violating,
            "violation_rate_pct": round(rows_violating / len(df) * 100, 1),
            "test_result": spec.result_if_violated if rows_violating else "PASS",
        })

    violation_columns = [
        "rule_id", "file", "row_number", "identifier", "dimension",
        "field", "rule", "observed_value", "test_result",
    ]
    return pd.DataFrame(results), pd.DataFrame(violations, columns=violation_columns)
