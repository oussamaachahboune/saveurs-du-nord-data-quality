"""Statistiques métier : profil des clients (âge) et indicateurs du catalogue produits."""

import plotly.graph_objects as go
import streamlit as st

from common import (
    COLORS, load_anomalies_with_proposals, load_csv, multiselect_filter, show_chart,
    stacked_bars, style_figure,
)

numeric_stats = load_csv("numeric_stats.csv")
category_stats = load_csv("category_stats.csv")
anomalies = load_anomalies_with_proposals()

STAT_COLUMNS = {
    "scope": "Périmètre",
    "n": "Valeurs",
    "mean": st.column_config.NumberColumn("Moyenne", format="%.2f"),
    "std": st.column_config.NumberColumn("Écart-type", format="%.2f"),
    "min": "Minimum",
    "q1": st.column_config.NumberColumn("Q1", format="%.2f"),
    "median": st.column_config.NumberColumn("Médiane", format="%.2f"),
    "q3": st.column_config.NumberColumn("Q3", format="%.2f"),
    "max": "Maximum",
}
SEVERITY = {"FAIL": 0, "REVIEW": 1, "INFO": 2}

st.title("Statistiques métier")

# =============================================================== Clients
st.header("Profil des clients")

ages = numeric_stats.loc[numeric_stats["field"].eq("age")].set_index("scope")
all_ages = ages.loc["Toutes les valeurs"]
valid_ages = ages.loc["Sans âges impossibles ni mineurs"]


def years(value: float) -> str:
    return f"{value:.1f} ans".replace(".", ",")


columns = st.columns(4)
columns[0].metric("Clients", int(all_ages["n"]))
columns[1].metric("Âge médian", years(all_ages["median"]),
                  help="Peu sensible aux âges aberrants : indicateur à retenir.")
columns[2].metric("Âge moyen", years(all_ages["mean"]),
                  help="Tiré vers le haut par les âges impossibles (150 et 172 ans).")
columns[3].metric("Âge médian des âges valides", years(valid_ages["median"]),
                  help=f"Calculé sur {int(valid_ages['n'])} clients, sans les âges hors de 0 à 120 ans "
                       "ni les âges inférieurs à 18 ans.")

st.markdown("**Moyenne et médiane de l'âge**")
fig = go.Figure()
for measure, label, color in [("mean", "Moyenne", COLORS["series"]),
                              ("median", "Médiane", COLORS["series_2"])]:
    fig.add_bar(
        y=ages.index, x=ages[measure], name=label, orientation="h",
        marker={"color": color, "line": {"color": COLORS["surface"], "width": 2}},
        hovertemplate=f"%{{y}}<br>{label} : %{{x:.1f}} ans<extra></extra>",
    )
fig.update_layout(barmode="group")
fig.update_yaxes(autorange="reversed")
fig.update_xaxes(title="Âge (ans)")
show_chart(style_figure(fig, height=260))
st.caption(
    "Les âges impossibles font monter la moyenne de 20 ans, alors que la médiane varie peu : "
    "tant que les âges ne sont pas corrigés, la médiane est l'indicateur à publier."
)

st.markdown("**Âges à investiguer**")
age_anomalies = anomalies.loc[anomalies["field"].eq("age")].copy()
age_anomalies["severity"] = age_anomalies["test_result"].map(SEVERITY)
age_review = (
    age_anomalies.sort_values("severity")
    .groupby("identifier", as_index=False)
    .agg(
        observed_value=("observed_value", "first"),
        test_result=("test_result", "first"),
        rules=("rule", lambda rules: " ; ".join(dict.fromkeys(rules))),
        strategy=("strategy", "first"),
    )
)
st.dataframe(
    age_review,
    hide_index=True,
    width="stretch",
    column_config={
        "identifier": "Client",
        "observed_value": "Âge déclaré",
        "test_result": st.column_config.TextColumn("Résultat", help="Niveau le plus grave parmi les règles violées."),
        "rules": "Règles violées",
        "strategy": "Traitement proposé",
    },
)

with st.expander("Statistiques détaillées de l'âge"):
    st.dataframe(ages.reset_index()[list(STAT_COLUMNS)], hide_index=True, width="stretch",
                 column_config=STAT_COLUMNS)
    st.caption(
        "« Sans âges impossibles ni mineurs » exclut les âges hors de 0 à 120 ans "
        "et les âges inférieurs à 18 ans, sans modifier les données."
    )

# =============================================================== Products
st.header("Catalogue produits")

categories = multiselect_filter("Catégorie", sorted(category_stats["categorie"]), key="business_category")
selection = category_stats.loc[category_stats["categorie"].isin(categories)]

columns = st.columns(4)
columns[0].metric("Produits", int(selection["products"].sum()))
columns[1].metric("Catégories", len(selection))
columns[2].metric("Stock total", f"{selection['total_stock'].sum():,.0f} unités".replace(",", " "),
                  help="Somme des stocks renseignés, y compris le stock négatif de PRD040.")
low_share = selection["low_stock"].sum() / max(selection["products"].sum(), 1) * 100
columns[3].metric("Produits en stock faible", f"{low_share:.0f} %",
                  help="Statut déclaré. Ce statut ne correspond pas à la quantité en stock "
                       "(voir la règle PRD-COH-02).")

ordered = selection.sort_values(["products", "median_price"]).set_index("categorie")
chart_height = max(320, 26 * len(ordered) + 100)
chart_columns = st.columns(2)
with chart_columns[0]:
    st.markdown("**Produits par catégorie et statut déclaré**")
    show_chart(stacked_bars(
        ordered, ["in_stock", "low_stock"], "produits", height=chart_height,
        colors={"in_stock": COLORS["series"], "low_stock": COLORS["series_2"]},
        labels={"in_stock": "En stock", "low_stock": "Stock faible"},
    ))
with chart_columns[1]:
    st.markdown("**Prix médian par catégorie (€)**")
    fig = go.Figure(go.Bar(
        y=ordered.index, x=ordered["median_price"], orientation="h", showlegend=False,
        marker={"color": COLORS["series"], "line": {"color": COLORS["surface"], "width": 2}},
        customdata=ordered[["mean_price", "min_price", "max_price"]],
        hovertemplate="%{y}<br>Prix médian : %{x:.2f} €<br>Prix moyen : %{customdata[0]:.2f} €"
                      "<br>Min : %{customdata[1]:.2f} € · Max : %{customdata[2]:.2f} €<extra></extra>",
    ))
    fig.update_xaxes(title="Prix médian (€)")
    show_chart(style_figure(fig, height=chart_height))

st.caption(
    "Le prix médian est affiché plutôt que la moyenne : le prix de 9 999,90 € (PRD090) "
    "porte la moyenne des « Coffrets & kits » au-delà de 1 693 €."
)

with st.expander("Indicateurs détaillés par catégorie"):
    st.dataframe(
        selection.sort_values("products", ascending=False),
        hide_index=True,
        width="stretch",
        column_config={
            "categorie": "Catégorie",
            "products": "Produits",
            "mean_price": st.column_config.NumberColumn("Prix moyen", format="%.2f €"),
            "median_price": st.column_config.NumberColumn("Prix médian", format="%.2f €"),
            "min_price": st.column_config.NumberColumn("Prix min", format="%.2f €"),
            "max_price": st.column_config.NumberColumn("Prix max", format="%.2f €"),
            "total_stock": st.column_config.NumberColumn("Stock total", format="%.0f"),
            "missing_stock": "Stocks manquants",
            "in_stock": "En stock",
            "low_stock": "Stock faible",
        },
    )

with st.expander("Statistiques des prix et des stocks du catalogue complet"):
    st.dataframe(
        numeric_stats.loc[numeric_stats["file"].eq("produits.csv"), ["field", *STAT_COLUMNS]],
        hide_index=True,
        width="stretch",
        column_config={"field": "Champ", **STAT_COLUMNS},
    )
