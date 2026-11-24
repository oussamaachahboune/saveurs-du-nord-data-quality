-- =============================================================================
-- 05_statistics.sql — Statistiques descriptives (Q16) et analyse par catégorie (Q17)
-- Prérequis : 01_views.sql, 04_quality_rules.sql
-- =============================================================================


-- name: v_numeric_stats — statistiques descriptives par champ numérique
-- Écart-type : SQLite n'a pas de fonction SQRT (extension mathématique absente).
-- La racine carrée de la variance est calculée par la méthode de Newton,
-- x(k+1) = (x(k) + variance / x(k)) / 2, dans une CTE récursive (60 itérations,
-- largement suffisant pour converger). La variance est celle de l'échantillon
-- (division par n - 1), comme la méthode std() de pandas.
DROP VIEW IF EXISTS v_numeric_stats;
CREATE VIEW v_numeric_stats AS
WITH RECURSIVE
moments AS (
    SELECT
        v.file,
        v.field,
        COUNT(*)     AS n,
        AVG(v.value) AS mean,
        MIN(v.value) AS min_value,
        MAX(v.value) AS max_value
    FROM v_numeric_values AS v
    GROUP BY v.file, v.field
),
variances AS (
    SELECT
        m.file,
        m.field,
        SUM((v.value - m.mean) * (v.value - m.mean)) / (m.n - 1) AS variance
    FROM moments AS m
    JOIN v_numeric_values AS v USING (file, field)
    GROUP BY m.file, m.field
),
square_roots (file, field, variance, x, iteration) AS (
    SELECT file, field, variance, MAX(variance, 1.0), 0 FROM variances
    UNION ALL
    SELECT file, field, variance, (x + variance / x) / 2, iteration + 1
    FROM square_roots
    WHERE iteration < 60
)
SELECT
    m.file,
    m.field,
    m.n,
    m.mean,
    s.x AS std,
    m.min_value,
    q.q1,
    q.median,
    q.q3,
    m.max_value
FROM moments AS m
JOIN square_roots AS s ON s.file = m.file AND s.field = m.field AND s.iteration = 60
JOIN v_quartiles  AS q ON q.file = m.file AND q.field = m.field;


-- name: Q16.1 - Statistiques des âges et des prix (toutes les valeurs numériques)
SELECT
    file,
    field,
    n,
    ROUND(mean, 2)   AS mean,
    ROUND(std, 2)    AS std,
    min_value,
    ROUND(q1, 2)     AS q1,
    ROUND(median, 2) AS median,
    ROUND(q3, 2)     AS q3,
    max_value
FROM v_numeric_stats
WHERE field IN ('age', 'prix_unitaire_eur', 'stock_unites')
ORDER BY file, field;

-- Interprétation :
-- - Âge : moyenne 60,3 ans contre une médiane de 42,5 ans. Les valeurs
--   150 et 172 tirent la moyenne vers le haut ; la médiane est plus robuste.
-- - Prix : moyenne 106,94 EUR contre une médiane de 4,85 EUR. Le seul prix
--   de 9 999,90 EUR (PRD090) multiplie la moyenne par plus de 20 et
--   l'écart-type dépasse 999 EUR.


-- name: Q16.2 - Moyenne et médiane après exclusion des valeurs invalides
-- Exclusion uniquement des lignes qui violent une règle de validité
-- (CLI-VAL-04 : âge hors 0-120 ; PRD-VAL-01 : prix négatif). Les données
-- brutes ne sont pas modifiées : il s'agit d'une analyse de sensibilité.
WITH valid_values AS (
    SELECT v.file, v.field, v.value
    FROM v_numeric_values AS v
    WHERE (v.field = 'age' AND v.source_row NOT IN (
               SELECT source_row FROM v_rule_violations WHERE rule_id = 'CLI-VAL-04'))
       OR (v.field = 'prix_unitaire_eur' AND v.source_row NOT IN (
               SELECT source_row FROM v_rule_violations WHERE rule_id = 'PRD-VAL-01'))
),
ranked AS (
    SELECT
        file,
        field,
        value,
        ROW_NUMBER() OVER (PARTITION BY field ORDER BY value) AS position,
        COUNT(*) OVER (PARTITION BY field) AS n
    FROM valid_values
)
SELECT
    file,
    field,
    n,
    ROUND(AVG(value), 2) AS mean,
    -- Médiane : valeur centrale (n impair) ou moyenne des deux valeurs centrales (n pair)
    ROUND(AVG(CASE WHEN position IN ((n + 1) / 2, (n + 2) / 2) THEN value END), 2) AS median,
    MIN(value) AS min_value,
    MAX(value) AS max_value
FROM ranked
GROUP BY file, field;

-- Interprétation :
-- - Sans les âges 150 et 172, la moyenne tombe à 35,1 ans (médiane 39,5) :
--   l'âge 0, valide au sens de CLI-VAL-04 mais improbable, reste inclus
--   et tire encore la moyenne vers le bas.
-- - Sans le prix négatif, la moyenne des prix reste à 108,07 EUR (médiane
--   4,90 EUR) : le prix de
--   9 999,90 EUR, valide au regard des règles, n'est pas exclu. Seule une
--   validation métier permettrait de le confirmer ou de le corriger.


-- name: Q17.1 - Catalogue par catégorie
-- La catégorie vide est affichée explicitement pour ne pas disparaître.
-- avg_price est calculée sur toutes les valeurs numériques, y compris les anomalies.
SELECT
    CASE WHEN TRIM(categorie) = '' THEN '(non renseignée)' ELSE categorie END AS categorie,
    COUNT(*)                         AS products,
    ROUND(AVG(prix_num), 2)          AS avg_price,
    MIN(prix_num)                    AS min_price,
    MAX(prix_num)                    AS max_price,
    SUM(stock_num)                   AS total_stock,
    SUM(stock_num IS NULL)           AS missing_stock,
    SUM(statut_stock = 'Stock faible') AS low_stock_products
FROM v_produits
GROUP BY 1
ORDER BY products DESC, categorie;

-- Interprétation :
-- - « Épicerie sucrée » est la catégorie la plus fournie (13 produits).
-- - Le prix moyen de « Coffrets & kits » (1 693,07 EUR) n'a pas de sens :
--   il est dû au seul prix de 9 999,90 EUR. Celui d'« Épicerie sucrée » est
--   tiré vers le bas par le prix négatif de PRD010.
-- - Le stock de « Plats préparés » inclut le stock négatif de PRD040 ;
--   celui d'« Épicerie sucrée » ignore le stock vide de PRD015.


-- name: Q17.2 - État des stocks
SELECT
    statut_stock,
    COUNT(*)              AS products,
    SUM(stock_num)        AS total_stock,
    MIN(stock_num)        AS min_stock,
    MAX(stock_num)        AS max_stock,
    SUM(stock_num <= 0)   AS products_without_stock
FROM v_produits
GROUP BY statut_stock
ORDER BY products DESC;
