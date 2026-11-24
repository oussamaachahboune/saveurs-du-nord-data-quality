"""Qualité : complétude par champ et anomalies par dimension et par champ."""

import streamlit as st

from common import (
    DIMENSIONS, RESULTS, horizontal_bars, load_anomalies_with_proposals, load_csv,
    multiselect_filter, show_chart, stacked_bars,
)

rule_results = load_csv("rule_results.csv")
profile = load_csv("column_profile.csv")
anomalies = load_anomalies_with_proposals()

st.title("Qualité")
st.caption("Complétude des champs et anomalies détectées par les règles de contrôle.")

# ---------------------------------------------------------------- Filters
filter_columns = st.columns(3)
with filter_columns[0]:
    files = multiselect_filter("Fichier", sorted(profile["file"].unique()), key="quality_file")
with filter_columns[1]:
    dimensions = multiselect_filter(
        "Dimension", [d for d in DIMENSIONS if d in set(rule_results["dimension"])], key="quality_dimension"
    )
with filter_columns[2]:
    fields = multiselect_filter(
        "Champ", sorted(profile.loc[profile["file"].isin(files), "field"].unique()), key="quality_field"
    )


def matches_fields(field_values):
    """A rule field such as 'ville|code_postal' matches if one of its fields is selected."""
    return field_values.str.split("|").apply(lambda parts: any(part in fields for part in parts))


selected_rules = rule_results.loc[
    rule_results["file"].isin(files)
    & rule_results["dimension"].isin(dimensions)
    & (rule_results["field"].eq("all_columns") | matches_fields(rule_results["field"]))
]
selected_anomalies = anomalies.loc[
    anomalies["file"].isin(files)
    & anomalies["dimension"].isin(dimensions)
    & (anomalies["field"].eq("all_columns") | matches_fields(anomalies["field"]))
]

# ---------------------------------------------------------------- Completeness
st.subheader("Complétude")

completeness = profile.loc[profile["file"].isin(files) & profile["field"].isin(fields)].copy()
completeness["label"] = completeness["file"].str.replace(".csv", "") + " · " + completeness["field"]
incomplete = completeness.loc[completeness["completeness_pct"].lt(100)].sort_values("completeness_pct",
                                                                                   ascending=False)
complete_count = len(completeness) - len(incomplete)

st.markdown(
    f"**{complete_count} champs sur {len(completeness)}** sont renseignés à 100 %. "
    "Une valeur est renseignée si elle n'est ni NULL, ni vide, ni composée uniquement d'espaces."
)
if not incomplete.empty:
    st.markdown("**Champs incomplets**")
    show_chart(horizontal_bars(
        incomplete["label"], incomplete["completeness_pct"], "Valeurs renseignées (%)",
        height=80 + 45 * len(incomplete), hover_unit=" %",
        text=[f"{value:.0f} % · {int(missing)} manquante(s)"
              for value, missing in zip(incomplete["completeness_pct"], incomplete["missing"])],
    ).update_xaxes(range=[0, 125]))

# ---------------------------------------------------------------- Anomalies
st.subheader("Anomalies par dimension et par champ")

if selected_anomalies.empty:
    st.success("Aucune anomalie pour la sélection.")
else:
    chart_columns = st.columns(2)
    by_dimension = (
        selected_anomalies.groupby(["dimension", "test_result"]).size().unstack(fill_value=0)
        .reindex(columns=RESULTS, fill_value=0)
    )
    by_dimension = by_dimension.loc[by_dimension.sum(axis=1).sort_values().index]
    with chart_columns[0]:
        st.markdown("**Par dimension**")
        show_chart(stacked_bars(by_dimension, RESULTS, "signalements"))

    by_field = (
        selected_anomalies
        .assign(label=selected_anomalies["file"].str.replace(".csv", "") + " · " + selected_anomalies["field"])
        .groupby(["label", "test_result"]).size().unstack(fill_value=0)
        .reindex(columns=RESULTS, fill_value=0)
    )
    by_field = by_field.loc[by_field.sum(axis=1).sort_values().index]
    with chart_columns[1]:
        st.markdown("**Par champ**")
        show_chart(stacked_bars(by_field, RESULTS, "signalements", height=max(360, 30 * len(by_field) + 80)))

# ---------------------------------------------------------------- Detailed tables
with st.expander(f"Résultat des {len(selected_rules)} règles de la sélection"):
    st.dataframe(
        selected_rules[["rule_id", "file", "dimension", "field", "rule",
                        "rows_violating", "violation_rate_pct", "test_result"]],
        hide_index=True,
        width="stretch",
        column_config={
            "rule_id": "Règle",
            "file": "Fichier",
            "dimension": "Dimension",
            "field": "Champ",
            "rule": "Description",
            "rows_violating": "Lignes concernées",
            "violation_rate_pct": st.column_config.NumberColumn("Taux", format="%.1f %%"),
            "test_result": "Résultat",
        },
    )

detail_columns = ["rule_id", "file", "row_number", "identifier", "field", "observed_value",
                  "test_result", "proposed_value", "strategy", "validation_source"]
with st.expander(f"Détail des {len(selected_anomalies)} anomalies et corrections proposées"):
    st.dataframe(
        selected_anomalies[detail_columns],
        hide_index=True,
        width="stretch",
        column_config={
            "rule_id": "Règle",
            "file": "Fichier",
            "row_number": "Ligne",
            "identifier": "Identifiant",
            "field": "Champ",
            "observed_value": "Valeur observée",
            "test_result": "Résultat",
            "proposed_value": st.column_config.TextColumn("Valeur proposée", width="medium"),
            "strategy": st.column_config.TextColumn("Stratégie", width="medium"),
            "validation_source": st.column_config.TextColumn("Source de validation", width="medium"),
        },
    )
    st.caption(
        "Les corrections sont des propositions à valider : aucune donnée n'a été modifiée. "
        "Les signaux INFO n'ont pas de proposition, car une valeur extrême n'est pas une erreur."
    )
    st.download_button(
        "Télécharger le détail (CSV)",
        selected_anomalies[detail_columns].to_csv(sep=";", index=False).encode("utf-8-sig"),
        file_name="anomalies_saveurs_du_nord.csv",
        mime="text/csv",
    )
