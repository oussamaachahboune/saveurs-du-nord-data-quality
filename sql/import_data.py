"""Import des CSV bruts dans la base SQLite data/saveurs.db.

Méthode d'import et adaptations :
- Séparateur : point-virgule (module csv, delimiter=";").
- Encodage : UTF-8 avec BOM. L'encodage "utf-8-sig" retire le BOM ; sans cela,
  le premier en-tête deviendrait "\\ufeffid_client" et la colonne serait
  impossible à interroger par son nom.
- Types : toutes les colonnes sont importées en TEXT, sans conversion.
  Les cellules vides restent des chaînes vides '' (et non NULL), comme
  dans le notebook Python. Les conversions numériques sont faites dans
  les vues de sql/01_views.sql, ce qui permet de détecter les valeurs
  non convertibles au lieu de les perdre.
- Traçabilité : une colonne source_row (1 = première ligne après l'en-tête)
  est ajoutée. Elle correspond à row_number dans les exports Python.

Tables créées :
- clients_raw, produits_raw : données brutes ;
- rules_catalog, ref_villes_cp : référentiels du dossier rules/ ;
- python_rule_results : résultats Python (outputs/rule_results.csv),
  importés s'ils existent, pour comparer SQL et Python (sql/07_sql_vs_python.sql) ;
- import_metadata : pour chaque fichier de données, nombre de lignes et de
  colonnes, empreinte SHA-256 (version du fichier analysé) et date d'import.

Les CSV d'origine ne sont jamais modifiés : la base est recréée à chaque import.
"""

from __future__ import annotations

import csv
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "saveurs.db"

SOURCES = {
    "clients_raw": PROJECT_ROOT / "data" / "raw" / "clients.csv",
    "produits_raw": PROJECT_ROOT / "data" / "raw" / "produits.csv",
    "rules_catalog": PROJECT_ROOT / "rules" / "rules_catalog.csv",
    "ref_villes_cp": PROJECT_ROOT / "rules" / "ref_villes_cp.csv",
    "python_rule_results": PROJECT_ROOT / "outputs" / "rule_results.csv",
}

# Only the raw data files get a source_row column
TRACKED_TABLES = {"clients_raw", "produits_raw"}
OPTIONAL_TABLES = {"python_rule_results"}


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, delimiter=";")
        header = next(reader)
        rows = list(reader)

    for line_number, row in enumerate(rows, start=2):
        if len(row) != len(header):
            raise ValueError(
                f"{path.name}, line {line_number}: {len(row)} fields, "
                f"{len(header)} expected"
            )
    return header, rows


def load_table(connection: sqlite3.Connection, table: str, path: Path) -> int:
    header, rows = read_csv(path)

    if table in TRACKED_TABLES:
        connection.execute(
            "INSERT INTO import_metadata VALUES (?, ?, ?, ?, ?, ?)",
            (
                path.name,
                table,
                len(rows),
                len(header),
                hashlib.sha256(path.read_bytes()).hexdigest(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        header = ["source_row", *header]
        rows = [[str(position), *row] for position, row in enumerate(rows, start=1)]

    columns = ", ".join(
        f'"{name}" INTEGER' if name == "source_row" else f'"{name}" TEXT'
        for name in header
    )
    placeholders = ", ".join("?" for _ in header)

    connection.execute(f'DROP TABLE IF EXISTS "{table}"')
    connection.execute(f'CREATE TABLE "{table}" ({columns})')
    connection.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)
    return len(rows)


def import_all(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE import_metadata (file TEXT, table_name TEXT, row_count INTEGER, "
            "column_count INTEGER, sha256 TEXT, imported_at TEXT)"
        )
        for table, path in SOURCES.items():
            if not path.exists():
                if table in OPTIONAL_TABLES:
                    print(f"{table}: skipped ({path.name} not found, run notebook 03 first)")
                    continue
                raise FileNotFoundError(
                    f"{path} introuvable : placer les CSV bruts dans data/raw/ (voir README)."
                )
            count = load_table(connection, table, path)
            print(f"{table}: {count} rows imported from {path.relative_to(PROJECT_ROOT)}")

    print(f"Database: {db_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    import_all()
