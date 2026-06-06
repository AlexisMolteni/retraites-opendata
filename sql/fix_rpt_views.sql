-- ============================================================
-- CORRECTION DES VUES RPT.* — adapte aux données réelles
-- fact.Montants : type_droit = 'TOTAL', genre = 'T' uniquement
-- ============================================================

USE RetraitesOpenData;
GO


-- 1. v_PensionVsInflation — corrige le filtre type_droit
CREATE OR ALTER VIEW rpt.v_PensionVsInflation AS
WITH base AS (
    SELECT
        a.annee,
        MAX(CASE WHEN g.code = 'T' THEN m.montant_euros END) AS montant_moyen_cnav
    FROM fact.Montants m
    JOIN dim.Annee     a ON a.annee_id      = m.annee_id
    JOIN dim.Genre     g ON g.genre_id      = m.genre_id
    JOIN dim.TypeDroit d ON d.type_droit_id = m.type_droit_id
    WHERE m.mesure = 'montant_global'
      AND d.code   = 'TOTAL'
    GROUP BY a.annee
)
SELECT
    b.annee,
    b.montant_moyen_cnav,
    ie.valeur                                               AS inflation_pct,
    -- Montant réel approximatif (base 100 = première année)
    ROUND(b.montant_moyen_cnav / NULLIF(
        (SELECT SUM(ie2.valeur / 100.0 + 1)
         FROM ext.INSEE_IndicesEconomiques ie2
         WHERE ie2.annee BETWEEN 2000 AND b.annee
           AND ie2.indicateur = 'INFLATION_PCT'), 0), 2)    AS montant_cnav_deflate_approx
FROM base b
LEFT JOIN ext.INSEE_IndicesEconomiques ie
    ON ie.annee = b.annee AND ie.indicateur = 'INFLATION_PCT';
GO


-- 2. v_CompaisonRegimes — corrige type_droit + indicateur DREES
CREATE OR ALTER VIEW rpt.v_CompaisonRegimes AS
SELECT
    a.annee,
    -- CNAV montant moyen tous droits
    MAX(CASE WHEN m.mesure = 'montant_global' AND dr.code = 'TOTAL' AND g.code = 'T'
             THEN m.montant_euros END)                       AS pension_moy_cnav,
    -- Pension brute mensuelle tous régimes DREES (H/F/T)
    MAX(CASE WHEN dp.indicateur = 'PENSION_BRUTE_MOIS_DD_MAJ' AND dp.genre_code = 'F'
             THEN dp.valeur END)                             AS pension_brute_drees_f,
    MAX(CASE WHEN dp.indicateur = 'PENSION_BRUTE_MOIS_DD_MAJ' AND dp.genre_code = 'H'
             THEN dp.valeur END)                             AS pension_brute_drees_h,
    MAX(CASE WHEN dp.indicateur = 'PENSION_BRUTE_MOIS_DD_MAJ' AND dp.genre_code = 'T'
             THEN dp.valeur END)                             AS pension_brute_drees_t,
    -- Rapport CNAV / tous régimes (%)
    ROUND(
        100.0 * MAX(CASE WHEN m.mesure = 'montant_global' AND dr.code = 'TOTAL' AND g.code = 'T'
                         THEN m.montant_euros END)
        / NULLIF(MAX(CASE WHEN dp.indicateur = 'PENSION_BRUTE_MOIS_DD_MAJ' AND dp.genre_code = 'T'
                          THEN dp.valeur END), 0)
    , 1)                                                     AS part_cnav_pct
FROM dim.Annee a
LEFT JOIN fact.Montants m  ON m.annee_id = a.annee_id
LEFT JOIN dim.TypeDroit dr ON dr.type_droit_id = m.type_droit_id
LEFT JOIN dim.Genre g      ON g.genre_id = m.genre_id
LEFT JOIN ext.DREES_PensionsMultiRegimes dp
    ON dp.annee = a.annee AND dp.regime_id = 99
WHERE a.annee BETWEEN 1974 AND 2025
GROUP BY a.annee;
GO


-- 3. v_DashboardPrincipal — corrige le produit cartésien sur les dimensions
CREATE OR ALTER VIEW rpt.v_DashboardPrincipal AS
SELECT
    a.annee,
    -- Effectifs CNAV total (tous genres, carsat TOTAL)
    (SELECT SUM(f2.nb_retraites)
     FROM fact.RetraitesEffectifs f2
     JOIN dim.CARSAT c2 ON c2.carsat_id = f2.carsat_id AND c2.code = 'TOTAL'
     WHERE f2.annee_id = a.annee_id)                         AS retraites_total_cnav,
    -- Montant moyen CNAV
    (SELECT MAX(m2.montant_euros)
     FROM fact.Montants m2
     JOIN dim.TypeDroit d2 ON d2.type_droit_id = m2.type_droit_id AND d2.code = 'TOTAL'
     JOIN dim.Genre g2     ON g2.genre_id = m2.genre_id AND g2.code = 'T'
     WHERE m2.annee_id = a.annee_id AND m2.mesure = 'montant_global') AS pension_moy_cnav,
    -- Âge moyen de départ tous droits
    (SELECT MAX(ag2.valeur)
     FROM fact.Ages ag2
     JOIN dim.Genre g2 ON g2.genre_id = ag2.genre_id AND g2.code = 'T'
     WHERE ag2.annee_id = a.annee_id AND ag2.mesure = 'age_moyen_attribution') AS age_moyen_depart,
    -- Inflation
    MAX(ie.valeur)                                            AS inflation_pct,
    -- Espérance de vie à 60 ans
    MAX(CASE WHEN ev.genre_code = 'F' AND ev.age_reference = 60
             THEN ev.esperance_annees END)                   AS esperance_vie_60_f,
    MAX(CASE WHEN ev.genre_code = 'H' AND ev.age_reference = 60
             THEN ev.esperance_annees END)                   AS esperance_vie_60_h,
    -- Réforme éventuelle
    MAX(ref.nom)                                              AS reforme_annee
FROM dim.Annee a
LEFT JOIN ext.INSEE_IndicesEconomiques ie
    ON ie.annee = a.annee AND ie.indicateur = 'INFLATION_PCT'
LEFT JOIN ext.INSEE_EsperanceVie ev
    ON ev.annee = a.annee AND ev.type_mesure = 'conjoncturelle'
LEFT JOIN ext.COR_Reformes ref
    ON ref.annee = a.annee
WHERE a.annee BETWEEN 1974 AND 2040
GROUP BY a.annee, a.annee_id;
GO


-- Vérification rapide
SELECT annee, retraites_total_cnav, pension_moy_cnav, age_moyen_depart,
       inflation_pct, esperance_vie_60_f, esperance_vie_60_h, reforme_annee
FROM rpt.v_DashboardPrincipal
WHERE annee BETWEEN 2000 AND 2023
ORDER BY annee;
GO
