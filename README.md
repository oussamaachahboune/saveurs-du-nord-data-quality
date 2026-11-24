# Audit et qualité des données — Les Saveurs du Nord

Travaux pratiques d'audit sur un jeu de données pédagogique fictif : un fichier clients (10 lignes) et un catalogue produits (100 lignes).
L'objectif est de profiler les données, de distinguer les violations d'intégrité des problèmes de qualité, puis de restituer les résultats en SQL, Python et dans un tableau de bord.

## Avancement

| Partie | Contenu | Livrable |
|---|---|---|
| 1 | Inventaire et profilage initial | [`notebooks/01_data_profiling.ipynb`](notebooks/01_data_profiling.ipynb) |
| 2 | Audit d'intégrité | [`notebooks/02_integrity_audit.ipynb`](notebooks/02_integrity_audit.ipynb) |
| 3 | Audit des dimensions de qualité | [`notebooks/03_quality_dimensions.ipynb`](notebooks/03_quality_dimensions.ipynb), [`outputs/anomalies.csv`](outputs/anomalies.csv) |
| 4 | Mise en œuvre SQL (SQLite) | [`sql/`](sql/), [`outputs/sql_results.txt`](outputs/sql_results.txt) |
| 5 | Mise en œuvre Python / Pandas | à venir |
| 6 | Tableau de bord (Streamlit) | à venir |
| 7 | Rapport d'audit final | à venir |

## Structure

```
data/raw/            CSV bruts (non versionnés, voir ci-dessous)
notebooks/           Notebooks d'analyse, un par partie
rules/
  rules_catalog.csv  Référentiel unique des règles de contrôle
  ref_villes_cp.csv  Référentiel ville / code postal utilisé par CLI-COH-01
src/dq.py            Chargement des données et fonctions de contrôle partagées
sql/                 Import SQLite et requêtes SQL commentées (01 à 07)
outputs/             Résultats exportés (CSV, graphiques)
```

## Données

Les fichiers bruts ne sont pas versionnés. Avant toute exécution, placez-les dans `data/raw/` :

- `data/raw/clients.csv`
- `data/raw/produits.csv`

Ce sont des CSV séparés par des points-virgules, encodés en UTF-8 avec BOM.
Ils sont lus en texte (`dtype=str`, `keep_default_na=False`) et ne sont jamais modifiés : toutes les analyses portent sur des copies en mémoire.

## Règles de contrôle

Chaque règle est décrite une seule fois dans [`rules/rules_catalog.csv`](rules/rules_catalog.csv) : identifiant, fichier, dimension, champ, condition testée et résultat en cas de violation.
Les mêmes `rule_id` sont utilisés en Python, en SQL et dans le tableau de bord, ce qui permet de comparer les résultats.

| Résultat | Signification |
|---|---|
| `FAIL` | Anomalie **certaine** : une règle explicite (structure, format, domaine légal) est violée. |
| `REVIEW` | Anomalie **probable** : la règle repose sur une hypothèse métier à confirmer. |
| `INFO` | **À vérifier** : signal statistique (valeur extrême) qui n'est pas une erreur confirmée. |
| `PASS` | Aucune ligne ne viole la règle. |

Le numéro de ligne commence à 1, sans compter l'en-tête du CSV.

## Exécution

Le projet utilise [uv](https://docs.astral.sh/uv/) et Python 3.12.

```bash
uv sync
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Les notebooks peuvent aussi être ouverts dans VS Code ou Jupyter avec le noyau du `.venv`.

### Partie SQL

```bash
uv run python sql/run_all.py
```

Le script importe les CSV dans `data/saveurs.db` (non versionnée), exécute `sql/01_views.sql` à `sql/07_sql_vs_python.sql` dans l'ordre et enregistre les résultats dans `outputs/sql_results.txt`.
Le notebook 03 doit avoir été exécuté avant, car `07_sql_vs_python.sql` compare les résultats SQL à `outputs/rule_results.csv`.

Après l'import, les scripts peuvent aussi être exécutés avec la ligne de commande SQLite (`sqlite3 data/saveurs.db ".read sql/04_quality_rules.sql"`) ou dans DB Browser for SQLite.

| Fichier | Contenu |
|---|---|
| `import_data.py` | Import (séparateur `;`, BOM UTF-8, colonnes en TEXT) et métadonnées des fichiers |
| `01_views.sql` | Vues typées, format long, quartiles et bornes de Tukey |
| `02_profiling.sql` | Volumes, valeurs distinctes et manquantes, modalités |
| `03_integrity.sql` | Identifiants manquants et dupliqués, lignes dupliquées |
| `04_quality_rules.sql` | Les 33 règles du catalogue et valeurs hors domaine |
| `05_statistics.sql` | Statistiques des âges et des prix, analyse par catégorie |
| `06_quality_summary.sql` | Vues de synthèse des indicateurs de qualité |
| `07_sql_vs_python.sql` | Comparaison avec Python et explication des écarts possibles |
