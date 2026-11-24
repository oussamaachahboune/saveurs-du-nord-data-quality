"""Chargement des exports et éléments communs aux pages du tableau de bord.

Le tableau de bord lit uniquement les fichiers de outputs/ produits par les
notebooks 03 et 04 : il n'applique aucune règle lui-même, ce qui garantit
que ses chiffres sont ceux de Python (et donc de SQL, voir sql/07).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DB_PATH = PROJECT_ROOT / "data" / "saveurs.db"

REPO_URL = "https://github.com/oussamaachahboune/saveurs-du-nord-data-quality"

COLORS = {
    "series": "#2a78d6",
    "series_2": "#eb6834",
    "PASS": "#0ca30c",
    "FAIL": "#d03b3b",
    "REVIEW": "#fab219",
    "INFO": "#898781",
    "ink": "#0b0b0b",
    "ink_2": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "surface": "#fcfcfb",
}

RESULTS = ["FAIL", "REVIEW", "INFO"]
RESULT_LABELS = {
    "PASS": "PASS : aucune violation",
    "FAIL": "FAIL : certain",
    "REVIEW": "REVIEW : probable",
    "INFO": "INFO : à vérifier",
}
DIMENSIONS = [
    "Intégrité", "Complétude", "Validité", "Cohérence",
    "Exactitude", "Unicité", "Valeurs aberrantes",
]

OUTLIER_NOTE = (
    "Une valeur extrême n'est pas une erreur confirmée : les signaux `INFO` "
    "et les anomalies `REVIEW` doivent être investigués avec une source de "
    "référence avant toute correction."
)

PLOTLY_CONFIG = {"displayModeBar": False}


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = OUTPUT_DIR / name
    if not path.exists():
        st.error(
            f"Fichier `outputs/{name}` introuvable. Exécutez d'abord les notebooks "
            "03 et 04 (voir README)."
        )
        st.stop()
    return pd.read_csv(path, sep=";", encoding="utf-8-sig")


@st.cache_data
def load_anomalies_with_proposals() -> pd.DataFrame:
    """Table de suivi des anomalies, complétée par la proposition de correction."""
    anomalies = load_csv("anomalies.csv")
    proposals = load_csv("correction_proposals.csv")[
        ["rule_id", "row_number", "field", "proposed_value", "strategy", "validation_source"]
    ]
    merged = anomalies.merge(proposals, on=["rule_id", "row_number", "field"], how="left")

    # Display the observed value without the quotes used in the export ('150' -> 150)
    single_value = merged["observed_value"].str.fullmatch(r"'.*'", na=False)
    merged.loc[single_value, "observed_value"] = merged.loc[single_value, "observed_value"].str[1:-1]

    is_info = merged["test_result"].eq("INFO")
    merged.loc[is_info, "strategy"] = "Signal statistique : aucune correction"
    return merged.fillna({"proposed_value": "—", "strategy": "—", "validation_source": "—"})


def multiselect_filter(label: str, options: list[str], key: str) -> list[str]:
    """Filtre à choix multiples : aucune sélection signifie « tout »."""
    selected = st.multiselect(label, options, placeholder="Tous", key=key)
    return selected or list(options)


def show_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def style_figure(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font={"family": "Segoe UI, system-ui, sans-serif", "size": 13, "color": COLORS["ink_2"]},
        margin={"l": 10, "r": 30, "t": 40, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0,
                "title": None, "traceorder": "normal"},
        hoverlabel={"bgcolor": "white", "font_size": 13},
        bargap=0.35,
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], linecolor=COLORS["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], linecolor=COLORS["axis"], showgrid=False)
    return fig


def horizontal_bars(labels, values, value_label: str, color: str = COLORS["series"],
                    height: int = 300, text=None, hover_unit: str = "") -> go.Figure:
    """Une seule série en barres horizontales, avec étiquettes optionnelles en bout de barre."""
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation="h", showlegend=False,
        marker={"color": color, "line": {"color": COLORS["surface"], "width": 2}},
        hovertemplate=f"%{{y}} : %{{x}}{hover_unit}<extra></extra>",
    ))
    if text is not None:
        fig.add_scatter(y=labels, x=values, mode="text", text=text, textposition="middle right",
                        showlegend=False, hoverinfo="skip", textfont={"color": COLORS["ink_2"]})
    fig.update_xaxes(title=value_label)
    return style_figure(fig, height)


def stacked_bars(table: pd.DataFrame, columns: list[str], value_label: str,
                 height: int = 360, colors: dict | None = None,
                 labels: dict | None = None) -> go.Figure:
    """Barres horizontales empilées : une ligne par index, une couleur par colonne."""
    colors = colors or COLORS
    labels = labels or RESULT_LABELS
    fig = go.Figure()
    for column in columns:
        name = labels.get(column, column)
        fig.add_bar(
            y=table.index,
            x=table[column],
            name=name,
            orientation="h",
            marker={"color": colors.get(column, COLORS["series"]),
                    "line": {"color": COLORS["surface"], "width": 2}},
            hovertemplate=f"%{{y}}<br>{name} : %{{x}} {value_label}<extra></extra>",
        )
    totals = table[columns].sum(axis=1)
    fig.add_scatter(
        y=table.index, x=totals, mode="text", text=totals.astype(str),
        textposition="middle right", showlegend=False, hoverinfo="skip",
        textfont={"color": COLORS["ink_2"]},
    )
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title=value_label, range=[0, max(totals.max(), 1) * 1.15])
    return style_figure(fig, height)


def sql_parity_from_log() -> tuple[int, int] | None:
    """Bilan SQL / Python enregistré dans outputs/sql_results.txt (dernière requête de sql/07)."""
    path = OUTPUT_DIR / "sql_results.txt"
    if not path.exists():
        return None
    last_line = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()][-1]
    try:
        compared, identical = (int(value) for value in last_line.split())
    except ValueError:
        return None
    return identical, compared


def compare_with_sql(rule_results: pd.DataFrame) -> tuple[int, int] | None:
    """Compare les résultats Python à SQL : base locale si elle existe, sinon journal SQL versionné."""
    if not DB_PATH.exists():
        return sql_parity_from_log()
    try:
        with sqlite3.connect(DB_PATH) as connection:
            sql_results = pd.read_sql(
                "SELECT rule_id, rows_violating, test_result FROM v_rule_results", connection
            )
    except Exception:
        return None
    merged = rule_results.merge(sql_results, on="rule_id", suffixes=("_python", "_sql"))
    identical = (
        merged["rows_violating_python"].eq(merged["rows_violating_sql"])
        & merged["test_result_python"].eq(merged["test_result_sql"])
    )
    return int(identical.sum()), len(rule_results)
