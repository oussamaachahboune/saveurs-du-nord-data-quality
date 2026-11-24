-- =============================================================================
-- 03_integrity.sql — Clés primaires candidates et doublons (Q14)
-- Prérequis : import_data.py
--
-- Clés primaires candidates : id_client (clients) et id_produit (produits).
-- Elles ne peuvent être déclarées PRIMARY KEY que si elles sont renseignées
-- et uniques : les requêtes ci-dessous le vérifient.
-- =============================================================================


-- name: Q14.1 - Identifiants manquants (NULL, vides ou espaces seuls)
SELECT 'clients.csv' AS file, COUNT(*) AS missing_identifiers
FROM clients_raw
WHERE id_client IS NULL OR TRIM(id_client) = ''
UNION ALL
SELECT 'produits.csv', COUNT(*)
FROM produits_raw
WHERE id_produit IS NULL OR TRIM(id_produit) = '';


-- name: Q14.2 - Identifiants clients dupliqués (GROUP BY ... HAVING)
SELECT
    id_client,
    COUNT(*)                   AS occurrences,
    GROUP_CONCAT(source_row)   AS source_rows,
    GROUP_CONCAT(prenom || ' ' || nom, ' / ') AS clients
FROM clients_raw
WHERE TRIM(id_client) <> ''
GROUP BY id_client
HAVING COUNT(*) > 1;


-- name: Q14.3 - Identifiants produits dupliqués (GROUP BY ... HAVING)
SELECT
    id_produit,
    COUNT(*)                        AS occurrences,
    GROUP_CONCAT(source_row)        AS source_rows,
    GROUP_CONCAT(nom_produit, ' / ') AS produits
FROM produits_raw
WHERE TRIM(id_produit) <> ''
GROUP BY id_produit
HAVING COUNT(*) > 1;


-- name: Q14.4 - Synthèse : clés dupliquées et lignes concernées
WITH duplicated_keys AS (
    SELECT 'clients.csv' AS file, id_client AS identifier, COUNT(*) AS occurrences
    FROM clients_raw
    WHERE TRIM(id_client) <> ''
    GROUP BY id_client
    HAVING COUNT(*) > 1
    UNION ALL
    SELECT 'produits.csv', id_produit, COUNT(*)
    FROM produits_raw
    WHERE TRIM(id_produit) <> ''
    GROUP BY id_produit
    HAVING COUNT(*) > 1
)
SELECT
    file,
    COUNT(*)         AS duplicated_keys,
    SUM(occurrences) AS rows_involved
FROM duplicated_keys
GROUP BY file;


-- name: Q14.5 - Lignes entièrement dupliquées (toutes les colonnes sauf source_row)
-- À distinguer des identifiants répétés : ici, toutes les valeurs sont identiques.
SELECT 'clients.csv' AS file, COUNT(*) AS duplicated_row_groups, COALESCE(SUM(n), 0) AS rows_involved
FROM (
    SELECT COUNT(*) AS n
    FROM clients_raw
    GROUP BY id_client, prenom, nom, age, email, telephone, ville,
             code_postal, type_client, date_inscription, entreprise_exemple
    HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'produits.csv', COUNT(*), COALESCE(SUM(n), 0)
FROM (
    SELECT COUNT(*) AS n
    FROM produits_raw
    GROUP BY id_produit, nom_produit, categorie, conditionnement, prix_unitaire_eur,
             tva_pct, stock_unites, statut_stock, type_fournisseur, entreprise_exemple
    HAVING COUNT(*) > 1
);

-- Interprétation :
-- - Aucun identifiant manquant.
-- - Une clé dupliquée par fichier : CLI001 (Camille Leroy / Thomas Dubois)
--   et PRD001 (Gaufres artisanales / Spéculoos pur beurre), soit 2 lignes
--   concernées dans chaque fichier.
-- - Aucune ligne entièrement dupliquée : les identifiants répétés désignent
--   des entités différentes, pas des copies. Une contrainte PRIMARY KEY
--   refuserait l'import en l'état.
