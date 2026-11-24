"""Vue d'ensemble : constats principaux, volumes, règles exécutées et indicateurs de qualité."""

import streamlit as st

from common import (
    DIMENSIONS, REPO_URL, RESULTS, compare_with_sql, load_anomalies_with_proposals, load_csv,
    show_chart, stacked_bars,
)

rule_results = load_csv("rule_results.csv")
profile = load_csv("column_profile.csv")
run_metadata = load_csv("run_metadata.csv")
anomalies = load_anomalies_with_proposals()

st.title("Vue d'ensemble")
st.caption("Audit d'intégrité et de qualité des fichiers clients et produits de l'entreprise fictive Les Saveurs du Nord.")

# ---------------------------------------------------------------- Key findings
errors = anomalies.loc[anomalies["test_result"].isin(["FAIL", "REVIEW"])]
rows_with_errors = errors.groupby("file")["row_number"].nunique()

repeated_ids = anomalies.loc[anomalies["rule_id"].str.endswith("INT-02"), "identifier"].unique()
vat_errors = errors.loc[errors["field"].eq("tva_pct")]
vat_impossible = vat_errors.loc[vat_errors["test_result"].eq("FAIL"), "observed_value"]
impossible_rates = ", ".join(f"{float(value):g} %" for value in vat_impossible)
stock_status = errors.loc[errors["field"].eq("stock_unites|statut_stock"), "row_number"].nunique()
clients = run_metadata.set_index("file").loc["clients.csv", "rows"]

with st.container(border=True):
    st.markdown("#### En bref")
    st.markdown(
        f"""
- **Identifiants non uniques** : {", ".join(f"`{value}`" for value in repeated_ids)} désignent
  chacun deux entités différentes. Leurs données risquent d'être mélangées.
- **TVA** : {vat_errors["row_number"].nunique()} taux sont à revoir, dont {len(vat_impossible)} impossible ({impossible_rates}).
  Les prix TTC et les déclarations de TVA peuvent être faux.
- **Stocks** : pour {stock_status} produits, le statut déclaré ne correspond pas à la quantité en stock.
- **Fichier clients** : {rows_with_errors.get("clients.csv", 0)} fiches sur {clients} ont au moins une
  anomalie certaine ou probable (âge, contact, code postal ou identifiant).
"""
    )

# ---------------------------------------------------------------- Headline KPIs
flagged = anomalies["test_result"].value_counts()
first_row, second_row = st.columns(3), st.columns(3)
first_row[0].metric("Lignes analysées", int(run_metadata["rows"].sum()),
                    help="10 clients et 100 produits.")
first_row[1].metric("Règles exécutées", len(rule_results),
                    help="Règles du référentiel rules/rules_catalog.csv.")
first_row[2].metric("Règles en échec", int(rule_results["rows_violating"].gt(0).sum()),
                    help="Règles violées par au moins une ligne.")
second_row[0].metric("Anomalies certaines", int(flagged.get("FAIL", 0)),
                     help="Signalements FAIL : une règle explicite est violée.")
second_row[1].metric("Anomalies probables", int(flagged.get("REVIEW", 0)),
                     help="Signalements REVIEW : la règle repose sur une hypothèse métier à confirmer.")
second_row[2].metric("Signaux à vérifier", int(flagged.get("INFO", 0)),
                     help="Signalements INFO : valeurs statistiquement extrêmes, pas des erreurs confirmées.")

# ---------------------------------------------------------------- Per-file indicators
st.subheader("Indicateurs par fichier")

duplicated_keys = (
    anomalies.loc[anomalies["rule_id"].str.endswith("INT-02")]
    .groupby("file")["identifier"].nunique()
)
completeness = profile.groupby("file").agg(populated=("populated", "sum"), cells=("rows", "sum"))

file_indicators = run_metadata[["file", "rows", "columns"]].copy()
file_indicators["completeness_pct"] = file_indicators["file"].map(
    (completeness["populated"] / completeness["cells"] * 100).round(1)
)
file_indicators["duplicated_keys"] = file_indicators["file"].map(duplicated_keys).fillna(0).astype(int)
file_indicators["rows_with_errors"] = file_indicators["file"].map(rows_with_errors).fillna(0).astype(int)
file_indicators["clean_rows_pct"] = (
    (file_indicators["rows"] - file_indicators["rows_with_errors"]) / file_indicators["rows"] * 100
).round(1)

st.dataframe(
    file_indicators,
    hide_index=True,
    width="stretch",
    column_config={
        "file": "Fichier",
        "rows": "Lignes",
        "columns": "Colonnes",
        "completeness_pct": st.column_config.NumberColumn("Complétude", format="%.1f %%",
            help="Valeurs renseignées / valeurs attendues, toutes colonnes confondues."),
        "duplicated_keys": st.column_config.NumberColumn("Clés dupliquées",
            help="Identifiants utilisés par plusieurs lignes."),
        "rows_with_errors": st.column_config.NumberColumn("Lignes avec anomalie",
            help="Lignes qui violent au moins une règle FAIL ou REVIEW."),
        "clean_rows_pct": st.column_config.ProgressColumn("Lignes sans anomalie", format="%.0f %%",
            min_value=0, max_value=100,
            help="Part des lignes sans anomalie certaine ni probable."),
    },
)

# ---------------------------------------------------------------- Rules by dimension
st.subheader("Résultat des règles par dimension")

rules_by_dimension = (
    rule_results.groupby(["dimension", "test_result"]).size().unstack(fill_value=0)
    .reindex(index=DIMENSIONS[::-1], columns=["PASS", *RESULTS], fill_value=0)
)
show_chart(stacked_bars(rules_by_dimension, ["PASS", *RESULTS], "règles", height=340))
st.caption(
    "Chaque règle compte une fois, avec son résultat : PASS si aucune ligne ne la viole, "
    "sinon le niveau de certitude défini dans le référentiel."
)

# ---------------------------------------------------------------- Priority anomalies
st.subheader("Anomalies certaines à traiter en priorité")
priority = (
    anomalies.loc[anomalies["test_result"].eq("FAIL")]
    .groupby(["rule_id", "file", "field", "rule"], as_index=False)
    .agg(rows=("row_number", "nunique"),
         identifiers=("identifier", lambda values: ", ".join(dict.fromkeys(values))))
    .sort_values(["rows", "rule_id"], ascending=[False, True])
)
st.dataframe(
    priority,
    hide_index=True,
    width="stretch",
    column_config={
        "rule_id": "Règle",
        "file": "Fichier",
        "field": "Champ",
        "rule": "Description",
        "rows": "Lignes",
        "identifiers": "Identifiants",
    },
)

# ---------------------------------------------------------------- Consistency check
with st.expander("Concordance avec SQL et Python"):
    st.markdown(
        "Le tableau de bord n'applique aucune règle : il lit les fichiers exportés par les "
        "notebooks Python. Les mêmes règles sont implémentées en SQL "
        f"([`sql/04_quality_rules.sql`]({REPO_URL}/blob/main/sql/04_quality_rules.sql)) "
        "et comparées dans "
        f"[`sql/07_sql_vs_python.sql`]({REPO_URL}/blob/main/sql/07_sql_vs_python.sql)."
    )
    comparison = compare_with_sql(rule_results)
    if comparison is not None:
        identical, total = comparison
        if identical == total:
            st.success(f"{identical} règles sur {total} donnent le même résultat en SQL et en Python.")
        else:
            st.error(f"Seules {identical} règles sur {total} concordent entre SQL et Python.")

    counted = anomalies.groupby("rule_id")["row_number"].nunique()
    expected = rule_results.set_index("rule_id")["rows_violating"]
    if expected.eq(counted.reindex(expected.index, fill_value=0)).all():
        st.success("Le détail des anomalies est cohérent avec le résultat de chaque règle.")
    else:
        st.error("Le détail des anomalies ne correspond pas au résultat des règles.")
