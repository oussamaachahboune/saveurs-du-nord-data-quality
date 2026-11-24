"""Intégrité : clés primaires, identifiants répétés et doublons."""

import streamlit as st

from common import load_anomalies_with_proposals, load_csv, multiselect_filter

rule_results = load_csv("rule_results.csv")
anomalies = load_anomalies_with_proposals()

st.title("Intégrité")
st.caption(
    "Clés primaires candidates : `id_client` et `id_produit`. Une clé doit être "
    "renseignée et unique ; une ligne ne doit pas être copiée à l'identique."
)

files = multiselect_filter("Fichier", sorted(rule_results["file"].unique()), key="integrity_file")

key_rules = rule_results.loc[
    rule_results["dimension"].isin(["Intégrité", "Unicité"]) & rule_results["file"].isin(files)
]
key_anomalies = anomalies.loc[
    anomalies["dimension"].isin(["Intégrité", "Unicité"]) & anomalies["file"].isin(files)
]


def rows_for(suffix: str) -> int:
    return int(key_rules.loc[key_rules["rule_id"].str.endswith(suffix), "rows_violating"].sum())


repeated = key_anomalies.loc[key_anomalies["rule_id"].str.endswith("INT-02")]

columns = st.columns(2)
columns[0].metric("Identifiants répétés", repeated["identifier"].nunique(),
                  help="Valeurs d'identifiant utilisées par plusieurs lignes.")
columns[1].metric("Lignes concernées", rows_for("INT-02"),
                  help="Lignes qui portent un identifiant répété.")

entity_duplicates = int(key_rules.loc[key_rules["dimension"].eq("Unicité"), "rows_violating"].sum())
st.markdown(
    f"Autres contrôles : **{rows_for('INT-01')}** identifiant manquant, "
    f"**{rows_for('INT-03')}** ligne entièrement dupliquée et **{entity_duplicates}** doublon "
    "d'entité (même e-mail, même prénom et nom, ou même produit dans le même conditionnement)."
)

st.subheader("Identifiants à corriger")
if repeated.empty:
    st.success("Aucun identifiant répété pour la sélection.")
else:
    to_fix = repeated.groupby(["identifier", "file"], as_index=False).agg(
        rows=("row_number", lambda rows: ", ".join(map(str, sorted(rows)))),
        proposed_value=("proposed_value", "first"),
        validation_source=("validation_source", "first"),
    )
    st.dataframe(
        to_fix,
        hide_index=True,
        width="stretch",
        column_config={
            "identifier": "Identifiant",
            "file": "Fichier",
            "rows": st.column_config.TextColumn("Lignes", help="1 = première ligne après l'en-tête."),
            "proposed_value": st.column_config.TextColumn("Correction proposée", width="large"),
            "validation_source": st.column_config.TextColumn("Source de validation", width="medium"),
        },
    )

st.markdown(
    """
**Identifiant répété ou doublon ?** Les lignes qui partagent `CLI001` décrivent deux
clients différents, et celles qui partagent `PRD001` deux produits différents.
Ce ne sont pas des copies : supprimer une ligne ferait perdre un client ou un produit réel.
La correction consiste à attribuer un nouvel identifiant à l'une des deux lignes.

**Conséquences d'une clé non unique :** informations de deux entités fusionnées,
comptages faussés, opérations impossibles à rattacher à la bonne entité et
jointures qui multiplient les lignes.
"""
)

with st.expander("Détail des règles de clés et de doublons"):
    st.dataframe(
        key_rules[["rule_id", "file", "dimension", "field", "rule", "rows_violating", "test_result"]],
        hide_index=True,
        width="stretch",
        column_config={
            "rule_id": "Règle",
            "file": "Fichier",
            "dimension": "Dimension",
            "field": "Champ",
            "rule": "Description",
            "rows_violating": "Lignes concernées",
            "test_result": "Résultat",
        },
    )
