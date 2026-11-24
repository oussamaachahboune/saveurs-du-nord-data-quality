# Audit et qualité des données — Les Saveurs du Nord

Audit d'intégrité et de qualité d'un jeu de données pédagogique fictif : le fichier clients (10 lignes) et le catalogue produits (100 lignes) d'une entreprise régionale imaginaire des Hauts-de-France.

Le projet profile les données, sépare les violations d'intégrité des problèmes de qualité, formalise 33 règles de contrôle reproductibles et restitue les résultats en Python, en SQL et dans un tableau de bord Streamlit. Les mêmes règles donnent les mêmes résultats dans les trois outils.

**Outils :** Python 3.12, pandas, matplotlib, SQLite, Streamlit, Plotly, uv.

## Principaux résultats

| Constat | Impact |
|---|---|
| `CLI001` et `PRD001` désignent chacun deux entités différentes | Données de deux clients ou de deux produits mélangées, jointures faussées |
| 10 taux de TVA à revoir, dont un taux impossible de 99 % | Prix TTC et déclarations de TVA potentiellement faux |
| Le statut « Stock faible » ne correspond pas à la quantité en stock (30 produits) | Réapprovisionnements mal priorisés |
| Âges impossibles (150 et 172 ans) et âge de 0 an | L'âge moyen passe de 40 à 60 ans : la médiane est l'indicateur à retenir |
| E-mail mal formé, téléphone incomplet, code postal parisien pour Lens | Clients injoignables, livraisons et analyses géographiques erronées |
| 99,1 % des valeurs clients et 99,8 % des valeurs produits renseignées | La complétude n'est pas le problème principal |

Au total, 19 règles sur 33 sont violées : 14 anomalies certaines, 41 probables et 15 signaux statistiques à vérifier. Chaque anomalie certaine ou probable a une proposition de correction traçable ; aucune donnée n'a été modifiée.

## Contenu du projet

| Partie | Contenu | Livrable |
|---|---|---|
| 1 | Inventaire et profilage initial | [`notebooks/01_data_profiling.ipynb`](notebooks/01_data_profiling.ipynb) |
| 2 | Audit d'intégrité : clés, doublons, contraintes et table de suivi des violations | [`notebooks/02_integrity_audit.ipynb`](notebooks/02_integrity_audit.ipynb) |
| 3 | Audit des dimensions de qualité : complétude, validité, cohérence, exactitude, unicité, fraîcheur, valeurs aberrantes | [`notebooks/03_quality_dimensions.ipynb`](notebooks/03_quality_dimensions.ipynb) |
| 4 | Mise en œuvre SQL (SQLite) et comparaison avec Python | [`sql/`](sql/), [`outputs/sql_results.txt`](outputs/sql_results.txt) |
| 5 | Mise en œuvre Python : visualisations et propositions de correction | [`notebooks/04_python_audit.ipynb`](notebooks/04_python_audit.ipynb), [`outputs/figures/`](outputs/figures/) |
| 6 | Tableau de bord Streamlit | [`dashboard/`](dashboard/) |

## Structure

```
data/raw/            CSV bruts, jamais modifiés
notebooks/           Notebooks d'analyse (01 à 04)
rules/
  rules_catalog.csv  Référentiel unique des 33 règles de contrôle
  ref_villes_cp.csv  Référentiel ville / code postal
src/dq.py            Chargement des données et fonctions de contrôle partagées
sql/                 Import SQLite et requêtes SQL commentées (01 à 07)
dashboard/           Tableau de bord Streamlit (app.py, pages dans views/)
outputs/             Résultats exportés : règles, anomalies, corrections, statistiques, graphiques
```

## Données

| Fichier | Lignes | Colonnes | Contenu |
|---|---|---|---|
| [`data/raw/clients.csv`](data/raw/clients.csv) | 10 | 11 | Identifiant, coordonnées, ville, code postal, type de client, date d'inscription et âge |
| [`data/raw/produits.csv`](data/raw/produits.csv) | 100 | 10 | Identifiant, catégorie, conditionnement, prix, TVA, stock et statut du stock |

Les données sont **fictives et synthétiques** : elles ne concernent aucune personne ni entreprise réelle.
Ce sont des CSV séparés par des points-virgules, encodés en UTF-8 avec BOM.

Les fichiers bruts ne sont jamais modifiés. Ils sont lus en texte (`dtype=str`, `keep_default_na=False`) pour ne perdre aucune valeur : une lecture par défaut aurait converti les codes postaux en entiers et les stocks en décimaux. Toutes les analyses portent sur des copies en mémoire.

## Règles de contrôle

Chaque règle est décrite une seule fois dans [`rules/rules_catalog.csv`](rules/rules_catalog.csv) : identifiant, fichier, dimension, champ, condition testée et résultat en cas de violation.
Elle est implémentée avec le même `rule_id` en Python ([`src/dq.py`](src/dq.py)) et en SQL ([`sql/04_quality_rules.sql`](sql/04_quality_rules.sql)), ce qui permet de comparer les résultats.

| Résultat | Signification |
|---|---|
| `FAIL` | Anomalie **certaine** : une règle explicite (structure, format, domaine légal) est violée. |
| `REVIEW` | Anomalie **probable** : la règle repose sur une hypothèse métier à confirmer. |
| `INFO` | **À vérifier** : signal statistique (valeur extrême) qui n'est pas une erreur confirmée. |
| `PASS` | Aucune ligne ne viole la règle. |

Dans les tables de suivi, le numéro de ligne commence à 1, sans compter l'en-tête du CSV.

## Exécution

Le projet utilise [uv](https://docs.astral.sh/uv/) et Python 3.12. Les commandes se lancent depuis la racine du dépôt, dans cet ordre.

**1. Installer l'environnement**

```bash
uv sync
```

**2. Exécuter les notebooks** (ils produisent les fichiers de `outputs/`)

```bash
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Les notebooks peuvent aussi être ouverts dans VS Code ou Jupyter avec le noyau du `.venv`.

**3. Exécuter la partie SQL**

```bash
uv run python sql/run_all.py
```

Le script importe les CSV dans `data/saveurs.db` (non versionnée), exécute `sql/01_views.sql` à `sql/07_sql_vs_python.sql` dans l'ordre et enregistre les résultats dans `outputs/sql_results.txt`. La dernière requête compare les 33 règles à leurs résultats Python.

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

**4. Lancer le tableau de bord**

```bash
uv run streamlit run dashboard/app.py
```

## Tableau de bord

Le tableau de bord s'ouvre dans le navigateur (`http://localhost:8501`). Il lit uniquement les fichiers de `outputs/` et n'applique aucune règle lui-même : ses chiffres sont donc ceux de Python, eux-mêmes identiques à ceux de SQL.

| Page | Contenu |
|---|---|
| Vue d'ensemble | Constats principaux, volumes, règles exécutées et en échec, anomalies par niveau de certitude, indicateurs par fichier, anomalies certaines à traiter en priorité et contrôle de concordance avec SQL |
| Intégrité | Identifiants répétés et corrections proposées, identifiants manquants, lignes dupliquées et doublons d'entités |
| Qualité | Champs incomplets, anomalies par dimension et par champ, résultat de chaque règle et détail des anomalies, téléchargeable en CSV |
| Statistiques métier | Âge des clients (moyenne, médiane, âges à investiguer) et indicateurs du catalogue par catégorie |

Les pages Intégrité, Qualité et Statistiques métier proposent des filtres par fichier, dimension, champ ou catégorie.
La barre latérale affiche sur chaque page la date d'exécution de l'audit, la version des fichiers analysés et un rappel : une valeur extrême doit être investiguée avant d'être considérée comme une erreur.

Le contrôle de concordance interroge la base SQLite locale si elle existe ; sinon, il lit le bilan enregistré dans `outputs/sql_results.txt`.
Pour un déploiement, [`dashboard/requirements.txt`](dashboard/requirements.txt) ne contient que les dépendances du tableau de bord.

| Indicateur | Définition |
|---|---|
| Règles en échec | Règles violées par au moins une ligne |
| Anomalies certaines / probables / signaux | Nombre de signalements `FAIL`, `REVIEW` et `INFO` dans la table de suivi |
| Complétude | Valeurs renseignées (ni NULL, ni vides, ni espaces) / valeurs attendues |
| Clés dupliquées | Identifiants utilisés par plusieurs lignes |
| Lignes sans anomalie | Lignes qui ne violent aucune règle `FAIL` ou `REVIEW` |
| Version des fichiers (barre latérale) | 12 premiers caractères de l'empreinte SHA-256 du fichier brut : elle change dès que le fichier est modifié |

## Limites

- **Fraîcheur :** aucun fichier ne contient de date de mise à jour. L'actualité des données ne peut pas être mesurée ; elle est documentée comme une limite plutôt qu'estimée.
- **Hypothèses métier :** plusieurs règles reposent sur des hypothèses à valider, comme le seuil de stock faible (20 unités), la majorité des clients ou la TVA des cartes cadeaux. Leurs violations sont classées `REVIEW`.
- **Exactitude :** une valeur valide peut être fausse. Les anomalies d'exactitude signalées (prix, TVA, code postal) doivent être confirmées avec une source de référence : fiche tarifaire, service comptable ou base officielle des adresses.
