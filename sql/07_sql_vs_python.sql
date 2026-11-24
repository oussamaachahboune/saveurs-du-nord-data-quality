-- =============================================================================
-- 07_sql_vs_python.sql — Comparaison des résultats SQL et Python (Q19)
-- Prérequis : 06_quality_summary.sql et la table python_rule_results,
-- importée depuis outputs/rule_results.csv (notebook 03) par import_data.py.
-- =============================================================================


-- name: Q19.1 - Règles dont le résultat diffère entre SQL et Python
-- Résultat attendu : aucune ligne.
SELECT
    s.rule_id,
    s.rows_violating            AS sql_rows,
    CAST(p.rows_violating AS INTEGER) AS python_rows,
    s.test_result               AS sql_result,
    p.test_result               AS python_result
FROM v_rule_results AS s
LEFT JOIN python_rule_results AS p ON p.rule_id = s.rule_id
WHERE p.rule_id IS NULL
   OR s.rows_violating <> CAST(p.rows_violating AS INTEGER)
   OR s.test_result <> p.test_result;


-- name: Q19.2 - Bilan de la comparaison
SELECT
    COUNT(*) AS rules_compared,
    SUM(s.rows_violating = CAST(p.rows_violating AS INTEGER)
        AND s.test_result = p.test_result) AS identical_results
FROM v_rule_results AS s
JOIN python_rule_results AS p ON p.rule_id = s.rule_id;


-- Différences possibles entre SQL et Python, et choix retenus pour les éviter :
--
-- 1. NULL et chaîne vide. Un CSV ne distingue pas les deux. Par défaut, pandas
--    transforme une cellule vide en NaN, tandis que l'import SQL (module csv,
--    comme l'outil .import de SQLite) la charge en chaîne vide ''. Pour rester
--    comparables, Python lit les fichiers avec keep_default_na=False et les
--    deux outils considèrent une valeur manquante si elle est NULL ou si
--    TRIM(valeur) = ''. Avec les options par défaut de pandas, isna() compterait
--    3 valeurs manquantes et la requête SUM(value IS NULL) en compterait 0.
--
-- 2. Conversion des nombres. En SQLite, CAST('abc' AS REAL) renvoie 0 au lieu
--    d'une erreur : une valeur non numérique serait comptée comme un zéro.
--    Les vues testent donc le format avant de convertir, comme
--    pd.to_numeric(errors="coerce"), qui renvoie NaN. Limite : la notation
--    scientifique (1e5) est acceptée par pandas mais rejetée par le test SQL ;
--    le jeu de données n'en contient pas.
--
-- 3. Médiane et quartiles. SQLite n'a pas de fonction de percentile. Les quartiles
--    sont recalculés avec l'interpolation linéaire de pandas. Avec une autre méthode
--    (NTILE, valeur la plus proche), Q1 et Q3 seraient différents : par exemple,
--    pour les âges, le Q3 interpolé (48,25) deviendrait 49 ou 46.
--
-- 4. Écart-type. SQLite n'a pas de fonction SQRT : il est calculé par la
--    méthode de Newton. La variance de l'échantillon (n - 1) est utilisée, comme
--    dans pandas ; numpy.std utilise n par défaut et donnerait une valeur plus faible.
--
-- 5. Expressions régulières. SQLite n'a pas de REGEXP natif. Les formats sont
--    contrôlés avec GLOB, LENGTH et INSTR, qui reproduisent les expressions
--    régulières Python. GLOB ne couvre que l'espace et la tabulation, alors que
--    \s couvre aussi les autres blancs Unicode.
--
-- 6. Casse et accents. LOWER() et LIKE de SQLite ne traitent que les lettres
--    ASCII : « É » n'est pas converti en « é ». Les contrôles d'unicité
--    normalisés pourraient donc différer de Python sur des noms accentués.
--    Le jeu de données ne contient pas ce cas.
--
-- 7. Arrondis. Python arrondit au pair le plus proche, SQLite arrondit
--    au plus loin de zéro. Les taux comparés ici sont exacts à 0,1 près.
--
-- 8. Date d'exécution. La règle CLI-COH-02 dépend de la date du jour :
--    les deux exécutions doivent avoir lieu le même jour pour être comparables.
