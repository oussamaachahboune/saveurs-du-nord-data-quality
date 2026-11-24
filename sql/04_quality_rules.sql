-- =============================================================================
-- 04_quality_rules.sql — Règles de contrôle et valeurs hors domaine (Q15)
-- Prérequis : 01_views.sql
--
-- Chaque bloc implémente une règle de rules/rules_catalog.csv avec le même
-- rule_id qu'en Python (src/dq.py). La vue v_rule_violations renvoie une ligne
-- par (règle, ligne source, champ) en violation.
-- Résultats : FAIL = certain, REVIEW = probable, INFO = à vérifier.
-- =============================================================================


-- name: v_rule_violations — une ligne par violation
DROP VIEW IF EXISTS v_rule_violations;
CREATE VIEW v_rule_violations AS

-- ---------------------------------------------------------------- Intégrité
-- CLI-INT-01 / PRD-INT-01 : identifiant renseigné
          SELECT 'CLI-INT-01' AS rule_id, source_row, NULL AS field FROM clients_raw
          WHERE id_client IS NULL OR TRIM(id_client) = ''
UNION ALL SELECT 'PRD-INT-01', source_row, NULL FROM produits_raw
          WHERE id_produit IS NULL OR TRIM(id_produit) = ''

-- CLI-INT-02 / PRD-INT-02 : identifiant unique
UNION ALL SELECT 'CLI-INT-02', source_row, NULL FROM clients_raw
          WHERE TRIM(id_client) <> ''
            AND id_client IN (SELECT id_client FROM clients_raw GROUP BY id_client HAVING COUNT(*) > 1)
UNION ALL SELECT 'PRD-INT-02', source_row, NULL FROM produits_raw
          WHERE TRIM(id_produit) <> ''
            AND id_produit IN (SELECT id_produit FROM produits_raw GROUP BY id_produit HAVING COUNT(*) > 1)

-- CLI-INT-03 / PRD-INT-03 : aucune ligne entièrement dupliquée
UNION ALL SELECT 'CLI-INT-03', source_row, NULL FROM clients_raw
          WHERE (id_client, prenom, nom, age, email, telephone, ville, code_postal,
                 type_client, date_inscription, entreprise_exemple) IN (
              SELECT id_client, prenom, nom, age, email, telephone, ville, code_postal,
                     type_client, date_inscription, entreprise_exemple
              FROM clients_raw
              GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
              HAVING COUNT(*) > 1)
UNION ALL SELECT 'PRD-INT-03', source_row, NULL FROM produits_raw
          WHERE (id_produit, nom_produit, categorie, conditionnement, prix_unitaire_eur,
                 tva_pct, stock_unites, statut_stock, type_fournisseur, entreprise_exemple) IN (
              SELECT id_produit, nom_produit, categorie, conditionnement, prix_unitaire_eur,
                     tva_pct, stock_unites, statut_stock, type_fournisseur, entreprise_exemple
              FROM produits_raw
              GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
              HAVING COUNT(*) > 1)

-- ---------------------------------------------------------------- Complétude
-- CLI-COM-01, CLI-COM-02, PRD-COM-01 : les champs contrôlés sont lus dans le
-- catalogue (colonne field, valeurs séparées par |). Une ligne par champ vide.
UNION ALL SELECT r.rule_id, v.source_row, v.field
          FROM rules_catalog AS r
          JOIN v_field_values AS v
            ON v.file = r.file
           AND INSTR('|' || r.field || '|', '|' || v.field || '|') > 0
          WHERE r.dimension = 'Complétude'
            AND (v.value IS NULL OR TRIM(v.value) = '')

-- ---------------------------------------------------------------- Validité
-- CLI-VAL-01 : e-mail = une partie locale, un seul @, un domaine avec un point,
-- sans espace (équivalent de la regex [^@\s]+@[^@\s]+\.[^@\s]+)
UNION ALL SELECT 'CLI-VAL-01', source_row, NULL FROM clients_raw
          WHERE TRIM(email) <> ''
            AND NOT (
                    email NOT GLOB '*[ 	]*'
                AND LENGTH(email) - LENGTH(REPLACE(email, '@', '')) = 1
                AND INSTR(email, '@') > 1
                AND SUBSTR(email, INSTR(email, '@') + 1) GLOB '?*.?*'
            )

-- CLI-VAL-02 : téléphone français, après suppression des espaces, points et tirets
UNION ALL SELECT 'CLI-VAL-02', source_row, NULL FROM v_clients
          WHERE TRIM(telephone) <> ''
            AND telephone_digits NOT GLOB '0[1-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
            AND telephone_digits NOT GLOB '+33[1-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'

-- CLI-VAL-03 : date au format AAAA-MM-JJ et existante
UNION ALL SELECT 'CLI-VAL-03', source_row, NULL FROM v_clients
          WHERE TRIM(date_inscription) <> '' AND date_inscription_valid IS NULL

-- CLI-VAL-04 : âge entier entre 0 et 120
UNION ALL SELECT 'CLI-VAL-04', source_row, NULL FROM v_clients
          WHERE TRIM(age) <> ''
            AND (age_num IS NULL OR age_num <> CAST(age_num AS INTEGER)
                 OR age_num < 0 OR age_num > 120)

-- CLI-VAL-05 : client majeur (hypothèse métier)
UNION ALL SELECT 'CLI-VAL-05', source_row, NULL FROM v_clients
          WHERE age_num < 18

-- CLI-VAL-06 : code postal à 5 chiffres
UNION ALL SELECT 'CLI-VAL-06', source_row, NULL FROM clients_raw
          WHERE TRIM(code_postal) <> ''
            AND code_postal NOT GLOB '[0-9][0-9][0-9][0-9][0-9]'

-- CLI-VAL-07 : type de client autorisé
UNION ALL SELECT 'CLI-VAL-07', source_row, NULL FROM clients_raw
          WHERE TRIM(type_client) <> ''
            AND type_client NOT IN ('Particulier', 'Professionnel')

-- PRD-VAL-01 : prix numérique et non négatif
UNION ALL SELECT 'PRD-VAL-01', source_row, NULL FROM v_produits
          WHERE TRIM(prix_unitaire_eur) <> '' AND (prix_num IS NULL OR prix_num < 0)

-- PRD-VAL-02 : taux de TVA légal en France métropolitaine
UNION ALL SELECT 'PRD-VAL-02', source_row, NULL FROM v_produits
          WHERE TRIM(tva_pct) <> ''
            AND (tva_num IS NULL OR tva_num NOT IN (2.1, 5.5, 10.0, 20.0))

-- PRD-VAL-03 : stock entier et non négatif
UNION ALL SELECT 'PRD-VAL-03', source_row, NULL FROM v_produits
          WHERE TRIM(stock_unites) <> ''
            AND (stock_num IS NULL OR stock_num < 0 OR stock_num <> CAST(stock_num AS INTEGER))

-- PRD-VAL-04 : statut de stock autorisé
UNION ALL SELECT 'PRD-VAL-04', source_row, NULL FROM produits_raw
          WHERE TRIM(statut_stock) <> ''
            AND statut_stock NOT IN ('En stock', 'Stock faible')

-- ---------------------------------------------------------------- Cohérence
-- CLI-COH-01 : code postal cohérent avec la ville (référentiel ref_villes_cp)
UNION ALL SELECT 'CLI-COH-01', c.source_row, NULL FROM clients_raw AS c
          WHERE TRIM(c.code_postal) <> ''
            AND c.ville IN (SELECT ville FROM ref_villes_cp)
            AND NOT EXISTS (
                SELECT 1 FROM ref_villes_cp AS r
                WHERE r.ville = c.ville AND r.code_postal = c.code_postal)

-- CLI-COH-02 : date d'inscription non future (date d'exécution locale)
UNION ALL SELECT 'CLI-COH-02', source_row, NULL FROM v_clients
          WHERE date_inscription_valid > DATE('now', 'localtime')

-- PRD-COH-01 : un produit sans stock ne peut pas être déclaré disponible
UNION ALL SELECT 'PRD-COH-01', source_row, NULL FROM v_produits
          WHERE stock_num <= 0 AND statut_stock IN ('En stock', 'Stock faible')

-- PRD-COH-02 : Stock faible si et seulement si stock < 20 (seuil hypothétique)
UNION ALL SELECT 'PRD-COH-02', source_row, NULL FROM v_produits
          WHERE stock_num > 0
            AND statut_stock IN ('En stock', 'Stock faible')
            AND (statut_stock = 'Stock faible') <> (stock_num < 20)

-- ---------------------------------------------------------------- Exactitude
-- PRD-EXA-01 : boisson sans alcool au taux réduit (LIKE ignore la casse ASCII)
UNION ALL SELECT 'PRD-EXA-01', source_row, NULL FROM v_produits
          WHERE nom_produit LIKE '%sans alcool%' AND tva_num = 20

-- PRD-EXA-02 : carte cadeau sans TVA à l'émission
UNION ALL SELECT 'PRD-EXA-02', source_row, NULL FROM v_produits
          WHERE categorie = 'Cartes cadeaux' AND tva_num > 0

-- PRD-EXA-03 : confiserie au taux normal
UNION ALL SELECT 'PRD-EXA-03', source_row, NULL FROM v_produits
          WHERE categorie = 'Confiserie' AND tva_num IS NOT NULL AND tva_num <> 20

-- ---------------------------------------------------------------- Unicité
-- CLI-UNI-01 : e-mail non partagé (minuscules, sans espaces autour)
UNION ALL SELECT 'CLI-UNI-01', source_row, NULL FROM clients_raw
          WHERE TRIM(email) <> ''
            AND LOWER(TRIM(email)) IN (
                SELECT LOWER(TRIM(email)) FROM clients_raw
                WHERE TRIM(email) <> ''
                GROUP BY 1 HAVING COUNT(*) > 1)

-- CLI-UNI-02 : couple prénom + nom non répété
UNION ALL SELECT 'CLI-UNI-02', source_row, NULL FROM clients_raw
          WHERE (LOWER(TRIM(prenom)), LOWER(TRIM(nom))) IN (
                SELECT LOWER(TRIM(prenom)), LOWER(TRIM(nom)) FROM clients_raw
                GROUP BY 1, 2 HAVING COUNT(*) > 1)

-- PRD-UNI-01 : couple nom + conditionnement non répété
UNION ALL SELECT 'PRD-UNI-01', source_row, NULL FROM produits_raw
          WHERE (LOWER(TRIM(nom_produit)), LOWER(TRIM(conditionnement))) IN (
                SELECT LOWER(TRIM(nom_produit)), LOWER(TRIM(conditionnement)) FROM produits_raw
                GROUP BY 1, 2 HAVING COUNT(*) > 1)

-- ---------------------------------------------------------------- Valeurs aberrantes
-- CLI-OUT-01, PRD-OUT-01, PRD-OUT-02 : valeurs hors des bornes de Tukey
UNION ALL SELECT 'CLI-OUT-01', v.source_row, NULL
          FROM v_numeric_values AS v JOIN v_tukey_bounds AS b USING (file, field)
          WHERE v.file = 'clients.csv' AND v.field = 'age'
            AND (v.value < b.lower_bound OR v.value > b.upper_bound)
UNION ALL SELECT 'PRD-OUT-01', v.source_row, NULL
          FROM v_numeric_values AS v JOIN v_tukey_bounds AS b USING (file, field)
          WHERE v.file = 'produits.csv' AND v.field = 'prix_unitaire_eur'
            AND (v.value < b.lower_bound OR v.value > b.upper_bound)
UNION ALL SELECT 'PRD-OUT-02', v.source_row, NULL
          FROM v_numeric_values AS v JOIN v_tukey_bounds AS b USING (file, field)
          WHERE v.file = 'produits.csv' AND v.field = 'stock_unites'
            AND (v.value < b.lower_bound OR v.value > b.upper_bound);


-- name: v_anomalies — table de suivi des violations (même format que outputs/anomalies.csv)
-- Pour les règles multi-champs hors complétude, field reprend le champ du catalogue.
DROP VIEW IF EXISTS v_anomalies;
CREATE VIEW v_anomalies AS
SELECT
    v.rule_id,
    r.file,
    v.source_row AS row_number,
    f.value      AS identifier,
    r.dimension,
    COALESCE(v.field, r.field) AS field,
    r.rule,
    r.result_if_violated AS test_result
FROM v_rule_violations AS v
JOIN rules_catalog AS r ON r.rule_id = v.rule_id
JOIN v_field_values AS f
  ON f.file = r.file
 AND f.source_row = v.source_row
 AND f.field = CASE r.file WHEN 'clients.csv' THEN 'id_client' ELSE 'id_produit' END;


-- name: Q15.1 - Valeurs hors domaine (validité) avec la valeur observée
SELECT
    a.rule_id,
    a.row_number,
    a.identifier,
    a.field,
    o.value AS observed_value,
    a.test_result
FROM v_anomalies AS a
JOIN v_field_values AS o
  ON o.file = a.file AND o.source_row = a.row_number AND o.field = a.field
WHERE a.dimension = 'Validité'
ORDER BY a.rule_id, a.row_number;

-- Interprétation :
-- - Clients : e-mail mal formé (CLI004), téléphone incomplet (CLI006),
--   âges impossibles 150 et 172 (CLI005, CLI007), âge 0 (CLI009, probable
--   valeur par défaut).
-- - Produits : prix négatif (PRD010), TVA à 99 % (PRD030), stock négatif (PRD040).


-- name: Q15.2 - Incohérences entre champs et anomalies d'exactitude
SELECT
    a.rule_id,
    a.row_number,
    a.identifier,
    a.field,
    a.test_result
FROM v_anomalies AS a
WHERE a.dimension IN ('Cohérence', 'Exactitude')
ORDER BY a.rule_id, a.row_number;

-- Interprétation :
-- - CLI008 : Lens associée au code postal parisien 75001.
-- - PRD021 et PRD040 : stock nul ou négatif déclaré « En stock ».
-- - 28 produits contredisent le seuil hypothétique de 20 unités pour
--   « Stock faible » : le statut ne semble pas calculé à partir du stock.
-- - 9 taux de TVA probablement erronés (boisson sans alcool, cartes cadeaux,
--   confiseries), à confirmer par le service comptable.
