-- =============================================================================
-- 02_profiling.sql — Volumes, valeurs distinctes et valeurs manquantes (Q13)
-- Prérequis : 01_views.sql
-- =============================================================================


-- name: Q13.1 - Volume : nombre de lignes et de colonnes par fichier
-- source_row est une colonne technique ajoutée à l'import : elle est exclue.
-- Le contrôle compare les volumes de la base à ceux relevés à l'import.
SELECT
    m.file,
    m.row_count AS rows_in_file,
    CASE m.table_name
        WHEN 'clients_raw' THEN (SELECT COUNT(*) FROM clients_raw)
        ELSE (SELECT COUNT(*) FROM produits_raw)
    END AS rows_in_database,
    (SELECT COUNT(*) FROM pragma_table_info(m.table_name) WHERE name <> 'source_row') AS column_count,
    SUBSTR(m.sha256, 1, 12) AS file_version,
    m.imported_at
FROM import_metadata AS m;


-- name: Q13.2 - Valeurs distinctes et manquantes par champ
-- Distinction demandée par le TP :
--   null_count            : valeur NULL (aucune ici : l'import conserve '' pour une cellule vide) ;
--   empty_string_count    : chaîne vide '' ;
--   whitespace_only_count : chaîne non vide composée uniquement d'espaces ;
--   completeness_pct      : valeurs renseignées / nombre de lignes.
-- COUNT(DISTINCT value) compte '' comme une valeur : distinct_populated l'exclut.
SELECT
    file,
    field,
    COUNT(*)                                                    AS row_count,
    COUNT(DISTINCT value)                                       AS distinct_values,
    COUNT(DISTINCT CASE WHEN TRIM(value) <> '' THEN value END)  AS distinct_populated,
    SUM(value IS NULL)                                          AS null_count,
    SUM(value = '')                                             AS empty_string_count,
    SUM(value <> '' AND TRIM(value) = '')                       AS whitespace_only_count,
    SUM(value <> TRIM(value))                                   AS surrounding_spaces_count,
    ROUND(100.0 * SUM(TRIM(value) <> '') / COUNT(*), 1)         AS completeness_pct
FROM v_field_values
GROUP BY file, field
ORDER BY file, completeness_pct, field;

-- Interprétation :
-- - clients.csv : 10 lignes x 11 colonnes ; produits.csv : 100 lignes x 10 colonnes.
-- - Trois valeurs manquantes, toutes des chaînes vides : email (CLI003, 90 %),
--   categorie (PRD005, 99 %) et stock_unites (PRD015, 99 %).
-- - Aucun espace superflu. id_client et id_produit n'ont que 9 et 99 valeurs
--   distinctes pour 10 et 100 lignes : un identifiant est répété dans chaque fichier.
-- - entreprise_exemple n'a qu'une valeur distincte : colonne constante, sans
--   intérêt analytique.


-- name: Q13.3 - Modalités des champs catégoriels
SELECT
    file,
    field,
    value,
    COUNT(*) AS occurrences
FROM v_field_values
WHERE field IN ('type_client', 'categorie', 'statut_stock', 'type_fournisseur', 'tva_pct')
GROUP BY file, field, value
ORDER BY file, field, occurrences DESC, value;

-- Interprétation :
-- - 20 catégories renseignées plus une valeur vide ; « Épicerie sucrée » est
--   la plus fréquente (13 produits).
-- - tva_pct : 5.5 (90 produits), 20.0 (9) et 99.0 (1), ce dernier hors domaine.
