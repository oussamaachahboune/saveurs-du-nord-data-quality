-- =============================================================================
-- 01_views.sql — Vues typées et vues techniques
-- SGBD : SQLite 3.45 (fonctions de fenêtre requises : SQLite >= 3.25)
-- Prérequis : python sql/import_data.py (tables *_raw en TEXT)
--
-- Les tables brutes restent en TEXT. Les vues ajoutent des colonnes
-- converties (suffixe _num ou _valid) qui valent NULL lorsque la valeur
-- est vide ou non convertible. Attention : CAST('abc' AS REAL) renvoie 0
-- en SQLite. On teste donc le format AVANT de convertir.
--
-- Test « valeur numérique » utilisé ci-dessous (équivalent de
-- pd.to_numeric(errors="coerce") pour ce jeu de données) :
--   la valeur, sans espaces autour, n'est pas vide, ne contient que des
--   chiffres, un point ou un signe, contient au moins un chiffre,
--   au plus un point et un signe uniquement en première position.
-- =============================================================================


-- name: v_clients — clients avec colonnes converties
DROP VIEW IF EXISTS v_clients;
CREATE VIEW v_clients AS
SELECT
    c.*,
    CASE
        WHEN TRIM(age) <> ''
         AND TRIM(age) NOT GLOB '*[^0-9.+-]*'
         AND TRIM(age) GLOB '*[0-9]*'
         AND TRIM(age) NOT GLOB '*.*.*'
         AND TRIM(age) NOT GLOB '?*[+-]*'
        THEN CAST(TRIM(age) AS REAL)
    END AS age_num,
    REPLACE(REPLACE(REPLACE(telephone, ' ', ''), '.', ''), '-', '') AS telephone_digits,
    CASE
        WHEN date_inscription GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
         -- date() normalise les dates impossibles (2025-02-30 -> 2025-03-02) :
         -- la comparaison avec la valeur d'origine les rejette.
         AND date(date_inscription) = date_inscription
        THEN date_inscription
    END AS date_inscription_valid
FROM clients_raw AS c;


-- name: v_produits — produits avec colonnes converties
DROP VIEW IF EXISTS v_produits;
CREATE VIEW v_produits AS
SELECT
    p.*,
    CASE
        WHEN TRIM(prix_unitaire_eur) <> ''
         AND TRIM(prix_unitaire_eur) NOT GLOB '*[^0-9.+-]*'
         AND TRIM(prix_unitaire_eur) GLOB '*[0-9]*'
         AND TRIM(prix_unitaire_eur) NOT GLOB '*.*.*'
         AND TRIM(prix_unitaire_eur) NOT GLOB '?*[+-]*'
        THEN CAST(TRIM(prix_unitaire_eur) AS REAL)
    END AS prix_num,
    CASE
        WHEN TRIM(tva_pct) <> ''
         AND TRIM(tva_pct) NOT GLOB '*[^0-9.+-]*'
         AND TRIM(tva_pct) GLOB '*[0-9]*'
         AND TRIM(tva_pct) NOT GLOB '*.*.*'
         AND TRIM(tva_pct) NOT GLOB '?*[+-]*'
        THEN CAST(TRIM(tva_pct) AS REAL)
    END AS tva_num,
    CASE
        WHEN TRIM(stock_unites) <> ''
         AND TRIM(stock_unites) NOT GLOB '*[^0-9.+-]*'
         AND TRIM(stock_unites) GLOB '*[0-9]*'
         AND TRIM(stock_unites) NOT GLOB '*.*.*'
         AND TRIM(stock_unites) NOT GLOB '?*[+-]*'
        THEN CAST(TRIM(stock_unites) AS REAL)
    END AS stock_num
FROM produits_raw AS p;


-- name: v_field_values — format long : une ligne par (fichier, ligne, champ)
-- Sert au profilage par champ (02_profiling.sql) et aux règles de complétude.
DROP VIEW IF EXISTS v_field_values;
CREATE VIEW v_field_values AS
          SELECT 'clients.csv' AS file, source_row, id_client AS identifier, 'id_client'          AS field, id_client          AS value FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'prenom',             prenom             FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'nom',                nom                FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'age',                age                FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'email',              email              FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'telephone',          telephone          FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'ville',              ville              FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'code_postal',        code_postal        FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'type_client',        type_client        FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'date_inscription',   date_inscription   FROM clients_raw
UNION ALL SELECT 'clients.csv', source_row, id_client, 'entreprise_exemple', entreprise_exemple FROM clients_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'id_produit',         id_produit         FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'nom_produit',        nom_produit        FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'categorie',          categorie          FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'conditionnement',    conditionnement    FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'prix_unitaire_eur',  prix_unitaire_eur  FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'tva_pct',            tva_pct            FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'stock_unites',       stock_unites       FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'statut_stock',       statut_stock       FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'type_fournisseur',   type_fournisseur   FROM produits_raw
UNION ALL SELECT 'produits.csv', source_row, id_produit, 'entreprise_exemple', entreprise_exemple FROM produits_raw;


-- name: v_numeric_values — valeurs numériques analysées (âges, prix, TVA, stocks)
DROP VIEW IF EXISTS v_numeric_values;
CREATE VIEW v_numeric_values AS
          SELECT 'clients.csv'  AS file, 'age'               AS field, source_row, age_num   AS value FROM v_clients  WHERE age_num   IS NOT NULL
UNION ALL SELECT 'produits.csv',         'prix_unitaire_eur',          source_row, prix_num           FROM v_produits WHERE prix_num  IS NOT NULL
UNION ALL SELECT 'produits.csv',         'tva_pct',                    source_row, tva_num            FROM v_produits WHERE tva_num   IS NOT NULL
UNION ALL SELECT 'produits.csv',         'stock_unites',               source_row, stock_num          FROM v_produits WHERE stock_num IS NOT NULL;


-- name: v_quartiles — Q1, médiane et Q3 par champ numérique
-- SQLite n'a pas de fonction de percentile. On reproduit la méthode par défaut
-- de pandas (interpolation linéaire) : pour une proportion p et n valeurs
-- triées v[0..n-1], h = (n - 1) * p et
--   quantile = v[floor(h)] + (h - floor(h)) * (v[floor(h) + 1] - v[floor(h)]).
-- h étant positif, CAST(h AS INTEGER) donne floor(h).
DROP VIEW IF EXISTS v_quartiles;
CREATE VIEW v_quartiles AS
WITH ranked AS (
    SELECT
        file,
        field,
        value,
        ROW_NUMBER() OVER (PARTITION BY file, field ORDER BY value) - 1 AS position,
        COUNT(*) OVER (PARTITION BY file, field) AS n
    FROM v_numeric_values
),
positions AS (
    SELECT DISTINCT r.file, r.field, r.n, p.proportion, (r.n - 1) * p.proportion AS h
    FROM ranked AS r
    CROSS JOIN (SELECT 0.25 AS proportion UNION ALL SELECT 0.5 UNION ALL SELECT 0.75) AS p
),
quantiles AS (
    SELECT
        pos.file,
        pos.field,
        pos.n,
        pos.proportion,
        low.value
            + (pos.h - CAST(pos.h AS INTEGER)) * (COALESCE(high.value, low.value) - low.value)
            AS quantile
    FROM positions AS pos
    JOIN ranked AS low
      ON low.file = pos.file AND low.field = pos.field
     AND low.position = CAST(pos.h AS INTEGER)
    LEFT JOIN ranked AS high
      ON high.file = pos.file AND high.field = pos.field
     AND high.position = CAST(pos.h AS INTEGER) + 1
)
SELECT
    file,
    field,
    n,
    MAX(CASE WHEN proportion = 0.25 THEN quantile END) AS q1,
    MAX(CASE WHEN proportion = 0.5  THEN quantile END) AS median,
    MAX(CASE WHEN proportion = 0.75 THEN quantile END) AS q3,
    MAX(CASE WHEN proportion = 0.75 THEN quantile END)
      - MAX(CASE WHEN proportion = 0.25 THEN quantile END) AS iqr
FROM quantiles
GROUP BY file, field;


-- name: v_tukey_bounds — bornes de Tukey [Q1 - 1,5 x IQR ; Q3 + 1,5 x IQR]
DROP VIEW IF EXISTS v_tukey_bounds;
CREATE VIEW v_tukey_bounds AS
SELECT
    file,
    field,
    q1 - 1.5 * iqr AS lower_bound,
    q3 + 1.5 * iqr AS upper_bound
FROM v_quartiles;
