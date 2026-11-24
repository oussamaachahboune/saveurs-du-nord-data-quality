"""Tableau de bord qualité des données — Les Saveurs du Nord.

Lancement depuis la racine du projet :
    uv run streamlit run dashboard/app.py
"""

import pandas as pd
import streamlit as st

from common import OUTLIER_NOTE, REPO_URL, load_csv

st.set_page_config(
    page_title="Qualité des données — Les Saveurs du Nord",
    layout="wide",
)

pages = st.navigation([
    st.Page("views/overview.py", title="Vue d'ensemble", default=True),
    st.Page("views/integrity.py", title="Intégrité", url_path="integrite"),
    st.Page("views/quality.py", title="Qualité", url_path="qualite"),
    st.Page("views/business.py", title="Statistiques métier", url_path="statistiques"),
])

# Shown on every page: context, run date, data source and outlier warning
run_metadata = load_csv("run_metadata.csv")
run_datetime = pd.to_datetime(run_metadata["run_datetime"].iloc[0])

with st.sidebar:
    st.markdown("**Les Saveurs du Nord**  \nAudit qualité des données")
    st.caption(
        "Projet d'audit d'intégrité et de qualité sur des données fictives : "
        "profilage, règles de contrôle en Python et SQL, propositions de correction."
    )
    st.markdown(f"[Code source sur GitHub]({REPO_URL})")

    st.markdown("**Sources analysées**")
    for row in run_metadata.itertuples(index=False):
        st.caption(f"`{row.file}` · {row.rows} lignes · {row.columns} colonnes · version `{row.sha256[:12]}`")
    st.caption(f"Exécution de l'audit : {run_datetime:%d/%m/%Y à %H:%M}")
    st.caption("Données fictives et synthétiques, fichiers bruts non modifiés.")
    st.info(OUTLIER_NOTE, icon="ℹ️")

pages.run()
