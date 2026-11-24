-- =============================================================================
-- 06_quality_summary.sql — Vues de synthèse des indicateurs de qualité (Q18)
-- Prérequis : 04_quality_rules.sql
-- =============================================================================


-- name: v_rule_results — une ligne par règle (même format que outputs/rule_results.csv)
-- rows_violating compte les lignes distinctes : une ligne avec deux champs
-- obligatoires vides n'est comptée qu'une fois.
DROP VIEW IF EXISTS v_rule_results;
CREATE VIEW v_rule_results AS
WITH row_counts AS (
    SELECT 'clients.csv' AS file, COUNT(*) AS rows_tested FROM clients_raw
    UNION ALL
    SELECT 'produits.csv', COUNT(*) FROM produits_raw
),
violation_counts AS (
    SELECT rule_id, COUNT(DISTINCT source_row) AS rows_violating
    FROM v_rule_violations
    GROUP BY rule_id
)
SELECT
    r.rule_id,
    r.file,
    r.dimension,
    r.field,
    r.rule,
    c.rows_tested,
    COALESCE(v.rows_violating, 0) AS rows_violating,
    ROUND(100.0 * COALESCE(v.rows_violating, 0) / c.rows_tested, 1) AS violation_rate_pct,
    CASE WHEN COALESCE(v.rows_violating, 0) > 0
         THEN r.result_if_violated ELSE 'PASS' END AS test_result
FROM rules_catalog AS r
JOIN row_counts AS c ON c.file = r.file
LEFT JOIN violation_counts AS v ON v.rule_id = r.rule_id;


-- name: v_quality_summary — indicateurs par fichier et par dimension
DROP VIEW IF EXISTS v_quality_summary;
CREATE VIEW v_quality_summary AS
SELECT
    file,
    dimension,
    COUNT(*)                                      AS rules_executed,
    SUM(rows_violating > 0)                       AS rules_violated,
    SUM(rows_violating)                           AS rows_flagged,
    SUM(CASE WHEN test_result = 'FAIL'   THEN rows_violating ELSE 0 END) AS fail_rows,
    SUM(CASE WHEN test_result = 'REVIEW' THEN rows_violating ELSE 0 END) AS review_rows,
    SUM(CASE WHEN test_result = 'INFO'   THEN rows_violating ELSE 0 END) AS info_rows
FROM v_rule_results
GROUP BY file, dimension;


-- name: v_quality_kpis — indicateurs clés par fichier
-- clean_rows : lignes qui ne violent aucune règle FAIL ou REVIEW
-- (les signaux INFO ne sont pas des erreurs).
DROP VIEW IF EXISTS v_quality_kpis;
CREATE VIEW v_quality_kpis AS
-- Volumes et version des fichiers : table import_metadata, remplie à l'import
-- (pragma_table_info est refusé dans une vue par la ligne de commande sqlite3).
WITH files AS (
    SELECT file, row_count, column_count, sha256 FROM import_metadata
),
completeness AS (
    SELECT file, ROUND(100.0 * SUM(TRIM(value) <> '') / COUNT(*), 1) AS completeness_pct
    FROM v_field_values
    GROUP BY file
),
flagged_rows AS (
    SELECT r.file, COUNT(DISTINCT v.source_row) AS rows_with_errors
    FROM v_rule_violations AS v
    JOIN rules_catalog AS r ON r.rule_id = v.rule_id
    WHERE r.result_if_violated IN ('FAIL', 'REVIEW')
    GROUP BY r.file
),
rules AS (
    SELECT file, COUNT(*) AS rules_executed, SUM(rows_violating > 0) AS rules_violated
    FROM v_rule_results
    GROUP BY file
),
duplicated_keys AS (
    SELECT 'clients.csv' AS file, COUNT(*) AS duplicated_keys
    FROM (SELECT id_client FROM clients_raw GROUP BY id_client HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'produits.csv', COUNT(*)
    FROM (SELECT id_produit FROM produits_raw GROUP BY id_produit HAVING COUNT(*) > 1)
)
SELECT
    f.file,
    f.row_count,
    f.column_count,
    c.completeness_pct,
    d.duplicated_keys,
    r.rules_executed,
    r.rules_violated,
    COALESCE(fr.rows_with_errors, 0)                        AS rows_with_errors,
    f.row_count - COALESCE(fr.rows_with_errors, 0)          AS clean_rows,
    ROUND(100.0 * (f.row_count - COALESCE(fr.rows_with_errors, 0)) / f.row_count, 1) AS clean_rows_pct,
    DATE('now', 'localtime')                                AS run_date,
    SUBSTR(f.sha256, 1, 12)                                 AS file_version
FROM files AS f
JOIN completeness    AS c  USING (file)
JOIN duplicated_keys AS d  USING (file)
JOIN rules           AS r  USING (file)
LEFT JOIN flagged_rows AS fr USING (file);


-- name: Q18.1 - Indicateurs clés par fichier
SELECT * FROM v_quality_kpis;


-- name: Q18.2 - Synthèse par dimension
SELECT * FROM v_quality_summary
ORDER BY file,
    CASE dimension
        WHEN 'Intégrité' THEN 1 WHEN 'Complétude' THEN 2 WHEN 'Validité' THEN 3
        WHEN 'Cohérence' THEN 4 WHEN 'Exactitude' THEN 5 WHEN 'Unicité' THEN 6
        ELSE 7
    END;


-- name: Q18.3 - Résultat de chaque règle
SELECT rule_id, field, rows_violating, violation_rate_pct, test_result
FROM v_rule_results
ORDER BY rule_id;

-- Interprétation :
-- - 33 règles exécutées (17 clients, 16 produits).
-- - Clients : 9 lignes sur 10 violent au moins une règle FAIL ou REVIEW ;
--   seule la fiche CLI010 est exempte d'anomalie certaine ou probable.
--   Le fichier est petit, mais presque chaque fiche porte un défaut différent.
-- - Produits : 41 lignes sur 100 sont signalées, 59 sont sans anomalie.
-- - Produits : la règle du seuil de stock faible (28 lignes) pèse
--   fortement sur le nombre de lignes signalées ; elle repose sur une
--   hypothèse à valider avant d'en tirer des conclusions.
