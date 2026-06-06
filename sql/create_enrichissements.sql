-- ============================================================
-- ENRICHISSEMENTS OPENDATA : INSEE · COR · DREES
-- SQL Server 2022 — base RetraitesOpenData
-- À exécuter après create_database.sql
-- ============================================================

USE RetraitesOpenData;
GO

-- ============================================================
-- SCHÉMA SOURCES EXTERNES
-- ============================================================

CREATE SCHEMA ext;   -- Données sources externes brutes
GO


-- ============================================================
-- INSEE — PYRAMIDE DES ÂGES
-- Source : https://www.insee.fr/fr/statistiques
-- Dataset : Estimations de population par sexe et groupe d'âge
-- ============================================================

CREATE TABLE ext.INSEE_PyramideAges (
    pyramide_id         INT             NOT NULL IDENTITY(1,1),
    annee               SMALLINT        NOT NULL,
    age                 TINYINT         NOT NULL,   -- âge révolu (0-99+)
    genre_code          CHAR(1)         NOT NULL,   -- 'H', 'F', 'T'
    population          BIGINT          NULL,       -- effectif au 1er janvier
    source_fichier      NVARCHAR(200)   NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ext_INSEE_PyramideAges PRIMARY KEY (pyramide_id),
    CONSTRAINT UQ_ext_INSEE_Pyramide UNIQUE (annee, age, genre_code),
    CONSTRAINT CK_ext_INSEE_Pyramide_genre CHECK (genre_code IN ('H','F','T'))
);
CREATE INDEX IX_ext_INSEE_Pyramide_annee ON ext.INSEE_PyramideAges (annee, genre_code);
GO


-- ============================================================
-- INSEE — ESPÉRANCE DE VIE
-- Espérance de vie à la naissance et aux âges clés (60, 62, 64, 65, 67 ans)
-- ============================================================

CREATE TABLE ext.INSEE_EsperanceVie (
    esperance_id        INT             NOT NULL IDENTITY(1,1),
    annee               SMALLINT        NOT NULL,
    genre_code          CHAR(1)         NOT NULL,   -- 'H', 'F', 'T'
    age_reference       TINYINT         NOT NULL,   -- 0=naissance, 60, 62, 64, 65, 67
    esperance_annees    DECIMAL(5,2)    NULL,       -- années de vie restantes
    type_mesure         NVARCHAR(20)    NOT NULL DEFAULT N'conjoncturelle',
        -- 'conjoncturelle', 'du_moment'
    source_fichier      NVARCHAR(200)   NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ext_INSEE_EsperanceVie PRIMARY KEY (esperance_id),
    CONSTRAINT UQ_ext_INSEE_EsperanceVie UNIQUE (annee, genre_code, age_reference, type_mesure)
);
GO


-- ============================================================
-- INSEE — INDICES ÉCONOMIQUES
-- IPC, SMPT (salaire moyen par tête), taux d'activité seniors
-- ============================================================

CREATE TABLE ext.INSEE_IndicesEconomiques (
    indice_id           INT             NOT NULL IDENTITY(1,1),
    annee               SMALLINT        NOT NULL,
    indicateur          NVARCHAR(50)    NOT NULL,
        -- 'IPC_BASE100_1998', 'INFLATION_PCT', 'SMPT_EUROS',
        -- 'TAUX_ACTIVITE_55_64', 'TAUX_ACTIVITE_60_64', 'PIB_HABITANT'
    genre_code          CHAR(1)         NOT NULL DEFAULT 'T',
    valeur              DECIMAL(12,4)   NULL,
    unite               NVARCHAR(20)    NULL,
    source_fichier      NVARCHAR(200)   NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ext_INSEE_IndicesEco PRIMARY KEY (indice_id),
    CONSTRAINT UQ_ext_INSEE_IndicesEco UNIQUE (annee, indicateur, genre_code)
);
-- Données inflation connues pour calibrage (à compléter via API INSEE)
INSERT INTO ext.INSEE_IndicesEconomiques (annee, indicateur, genre_code, valeur, unite) VALUES
(2000,'INFLATION_PCT','T', 1.8, '%'),
(2001,'INFLATION_PCT','T', 1.8, '%'),
(2002,'INFLATION_PCT','T', 1.9, '%'),
(2003,'INFLATION_PCT','T', 2.1, '%'),
(2004,'INFLATION_PCT','T', 2.1, '%'),
(2005,'INFLATION_PCT','T', 1.9, '%'),
(2006,'INFLATION_PCT','T', 1.9, '%'),
(2007,'INFLATION_PCT','T', 1.6, '%'),
(2008,'INFLATION_PCT','T', 3.2, '%'),
(2009,'INFLATION_PCT','T', 0.1, '%'),
(2010,'INFLATION_PCT','T', 1.7, '%'),
(2011,'INFLATION_PCT','T', 2.3, '%'),
(2012,'INFLATION_PCT','T', 2.2, '%'),
(2013,'INFLATION_PCT','T', 1.0, '%'),
(2014,'INFLATION_PCT','T', 0.6, '%'),
(2015,'INFLATION_PCT','T', 0.0, '%'),
(2016,'INFLATION_PCT','T', 0.2, '%'),
(2017,'INFLATION_PCT','T', 1.2, '%'),
(2018,'INFLATION_PCT','T', 1.8, '%'),
(2019,'INFLATION_PCT','T', 1.3, '%'),
(2020,'INFLATION_PCT','T', 0.5, '%'),
(2021,'INFLATION_PCT','T', 1.6, '%'),
(2022,'INFLATION_PCT','T', 5.9, '%'),
(2023,'INFLATION_PCT','T', 5.7, '%'),
(2024,'INFLATION_PCT','T', 2.3, '%');
GO


-- ============================================================
-- COR — RÉFORMES LÉGISLATIVES
-- Référentiel des grandes réformes du système de retraite
-- Source : https://www.cor-retraites.fr
-- ============================================================

CREATE TABLE ext.COR_Reformes (
    reforme_id          SMALLINT        NOT NULL IDENTITY(1,1),
    annee               SMALLINT        NOT NULL,
    nom                 NVARCHAR(100)   NOT NULL,
    description         NVARCHAR(MAX)   NULL,
    age_legal_avant     TINYINT         NULL,
    age_legal_apres     TINYINT         NULL,
    age_taux_plein_avant TINYINT        NULL,
    age_taux_plein_apres TINYINT        NULL,
    duree_cotis_avant   DECIMAL(4,1)    NULL,   -- en années
    duree_cotis_apres   DECIMAL(4,1)    NULL,
    impact_attendu      NVARCHAR(200)   NULL,
    CONSTRAINT PK_ext_COR_Reformes PRIMARY KEY (reforme_id)
);
INSERT INTO ext.COR_Reformes
    (annee, nom, description,
     age_legal_avant, age_legal_apres,
     age_taux_plein_avant, age_taux_plein_apres,
     duree_cotis_avant, duree_cotis_apres, impact_attendu)
VALUES
(1993, N'Réforme Balladur',
    N'Allongement progressif de la durée de cotisation pour le secteur privé ; indexation sur les prix.',
    60, 60, 65, 65, 37.5, 40.0,
    N'Recul de l''âge effectif de départ, baisse des pensions relatives'),
(2003, N'Réforme Fillon',
    N'Alignement public/privé, décote/surcote, allongement progressif à 41 ans.',
    60, 60, 65, 65, 40.0, 41.0,
    N'Harmonisation des régimes, incitation à travailler plus longtemps'),
(2007, N'Régimes spéciaux',
    N'Réforme des régimes spéciaux (RATP, SNCF, EDF…).',
    NULL, NULL, NULL, NULL, NULL, NULL,
    N'Convergence progressive des régimes spéciaux'),
(2010, N'Réforme Woerth',
    N'Relèvement de l''âge légal de 60 à 62 ans, âge du taux plein de 65 à 67 ans.',
    60, 62, 65, 67, 41.0, 41.5,
    N'Fort recul de l''âge de départ, mobilisation sociale majeure'),
(2014, N'Réforme Touraine',
    N'Allongement progressif de la durée à 43 ans (génération 1973+).',
    62, 62, 67, 67, 41.5, 43.0,
    N'Allongement des carrières sur le long terme'),
(2023, N'Réforme Borne',
    N'Relèvement de l''âge légal de 62 à 64 ans, accélération de l''allongement de la durée.',
    62, 64, 67, 67, 43.0, 43.0,
    N'Réforme très contestée, impact sur départs anticipés et carrières longues');
GO


-- ============================================================
-- COR — PROJECTIONS OFFICIELLES
-- Scénarios du rapport annuel du COR (horizon 2030-2070)
-- ============================================================

CREATE TABLE ext.COR_Scenarios (
    scenario_id     TINYINT         NOT NULL,
    code            NVARCHAR(20)    NOT NULL,
    libelle         NVARCHAR(80)    NOT NULL,
    croissance_pib  DECIMAL(4,2)    NULL,   -- % annuel
    description     NVARCHAR(200)   NULL,
    CONSTRAINT PK_ext_COR_Scenarios PRIMARY KEY (scenario_id)
);
INSERT INTO ext.COR_Scenarios VALUES
(1, 'PESSIMISTE',  N'Croissance 0,7 %/an',  0.7, N'Stagnation structurelle'),
(2, 'CENTRAL_BAS', N'Croissance 1,0 %/an',  1.0, N'Scénario central bas'),
(3, 'CENTRAL_HAUT',N'Croissance 1,3 %/an',  1.3, N'Scénario central haut (de référence)'),
(4, 'OPTIMISTE',   N'Croissance 1,8 %/an',  1.8, N'Reprise de la productivité');
GO

CREATE TABLE ext.COR_Projections (
    projection_id           INT             NOT NULL IDENTITY(1,1),
    scenario_id             TINYINT         NOT NULL,
    annee                   SMALLINT        NOT NULL,
    indicateur              NVARCHAR(60)    NOT NULL,
        -- 'NB_RETRAITES', 'DEPENSES_PCT_PIB', 'TAUX_REMPLACEMENT_NET',
        -- 'RATIO_ACTIFS_RETRAITES', 'PENSION_MOYENNE_EUROS'
    valeur                  DECIMAL(12,4)   NULL,
    unite                   NVARCHAR(20)    NULL,
    source_rapport          NVARCHAR(60)    NULL,   -- ex: 'Rapport COR juin 2023'
    date_import             DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ext_COR_Projections PRIMARY KEY (projection_id),
    CONSTRAINT FK_ext_COR_Proj_scenario FOREIGN KEY (scenario_id)
        REFERENCES ext.COR_Scenarios (scenario_id),
    CONSTRAINT UQ_ext_COR_Projections UNIQUE (scenario_id, annee, indicateur)
);
CREATE INDEX IX_ext_COR_Projections_annee ON ext.COR_Projections (annee, indicateur);
GO


-- ============================================================
-- DREES — RÉGIMES COMPLÉMENTAIRES & MULTI-RÉGIMES
-- Source : https://drees.solidarites-sante.gouv.fr
-- ============================================================

CREATE TABLE ext.DREES_Regimes (
    regime_id       SMALLINT        NOT NULL,
    code            NVARCHAR(20)    NOT NULL,
    libelle         NVARCHAR(100)   NOT NULL,
    type_regime     NVARCHAR(20)    NOT NULL,   -- 'base', 'complementaire', 'special'
    CONSTRAINT PK_ext_DREES_Regimes PRIMARY KEY (regime_id),
    CONSTRAINT UQ_ext_DREES_Regimes_code UNIQUE (code)
);
INSERT INTO ext.DREES_Regimes VALUES
(1,  'CNAV',        N'Caisse Nationale d''Assurance Vieillesse (régime général)',    N'base'),
(2,  'AGIRC_ARRCO', N'AGIRC-ARRCO (complémentaire salariés privés)',                 N'complementaire'),
(3,  'IRCANTEC',    N'IRCANTEC (contractuels de la fonction publique)',               N'complementaire'),
(4,  'CNRACL',      N'CNRACL (fonctionnaires territoriaux et hospitaliers)',          N'special'),
(5,  'FPE',         N'Fonction Publique d''État',                                    N'special'),
(6,  'MSA_SALARIES',N'MSA — Salariés agricoles',                                     N'base'),
(7,  'MSA_EXPLOITANTS',N'MSA — Exploitants agricoles',                               N'base'),
(8,  'SSI',         N'Sécurité Sociale des Indépendants (ex-RSI)',                   N'base'),
(9,  'CNAVPL',      N'Caisse Nationale des Professions Libérales',                   N'base'),
(10, 'CNBF',        N'Caisse Nationale des Barreaux Français (avocats)',             N'base'),
(11, 'SNCF',        N'Caisse de retraite du personnel SNCF',                         N'special'),
(12, 'RATP',        N'Caisse de retraite RATP',                                      N'special'),
(13, 'CNIEG',       N'Caisse Nationale des Industries Électriques et Gazières',      N'special'),
(99, 'TOUS_REGIMES',N'Ensemble des régimes (retraite globale)',                      N'total');
GO

CREATE TABLE ext.DREES_PensionsMultiRegimes (
    pension_id          INT             NOT NULL IDENTITY(1,1),
    annee               SMALLINT        NOT NULL,
    regime_id           SMALLINT        NOT NULL,
    genre_code          CHAR(1)         NOT NULL,   -- 'H', 'F', 'T'
    indicateur          NVARCHAR(50)    NOT NULL,
        -- 'NB_RETRAITES', 'PENSION_BRUTE_MOIS', 'PENSION_NETTE_MOIS',
        -- 'TAUX_REMPLACEMENT', 'PENSION_DROIT_PROPRE'
    valeur              DECIMAL(12,2)   NULL,
    unite               NVARCHAR(20)    NULL,
    source_fichier      NVARCHAR(200)   NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ext_DREES_Pensions PRIMARY KEY (pension_id),
    CONSTRAINT FK_ext_DREES_Pensions_regime FOREIGN KEY (regime_id)
        REFERENCES ext.DREES_Regimes (regime_id),
    CONSTRAINT UQ_ext_DREES_Pensions UNIQUE (annee, regime_id, genre_code, indicateur),
    CONSTRAINT CK_ext_DREES_Pensions_genre CHECK (genre_code IN ('H','F','T'))
);
CREATE INDEX IX_ext_DREES_Pensions_annee ON ext.DREES_PensionsMultiRegimes (annee, regime_id);
GO


-- ============================================================
-- TABLE DE LIAISON : croisements CNAV × sources externes
-- Permet de tracer quels faits CNAV sont enrichis avec quoi
-- ============================================================

CREATE TABLE meta.SourcesExternesLog (
    log_id              INT             NOT NULL IDENTITY(1,1),
    source              NVARCHAR(20)    NOT NULL,   -- 'INSEE', 'COR', 'DREES'
    indicateur          NVARCHAR(100)   NOT NULL,
    url_telechargement  NVARCHAR(500)   NULL,
    annee_donnees_min   SMALLINT        NULL,
    annee_donnees_max   SMALLINT        NULL,
    nb_lignes           INT             NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    statut              NVARCHAR(20)    NOT NULL DEFAULT N'EN_ATTENTE',
    CONSTRAINT PK_meta_SourcesExternesLog PRIMARY KEY (log_id)
);
-- Pré-remplir les URLs cibles
INSERT INTO meta.SourcesExternesLog (source, indicateur, url_telechargement, statut) VALUES
('INSEE', 'Pyramide des âges par sexe et groupe d''âge',
    'https://www.insee.fr/fr/statistiques/fichier/1893198/pop-totale-france.xlsx', 'EN_ATTENTE'),
('INSEE', 'Espérance de vie à divers âges',
    'https://www.insee.fr/fr/statistiques/fichier/6524724/t65_esp.xlsx', 'EN_ATTENTE'),
('INSEE', 'Indices des prix à la consommation',
    'https://www.insee.fr/fr/statistiques/serie/000641194', 'EN_ATTENTE'),
('INSEE', 'Taux d''activité par tranche d''âge',
    'https://www.insee.fr/fr/statistiques/serie/001595978', 'EN_ATTENTE'),
('COR',   'Projections système de retraite — rapport annuel',
    'https://www.cor-retraites.fr/simulateur/projections', 'EN_ATTENTE'),
('DREES', 'Les retraités et les retraites — édition annuelle',
    'https://drees.solidarites-sante.gouv.fr/publications/panoramas-de-la-drees/les-retraites-et-les-retraites', 'EN_ATTENTE'),
('DREES', 'Données AGIRC-ARRCO',
    'https://drees.solidarites-sante.gouv.fr/sources-outils-et-enquetes/les-comptes-de-la-protection-sociale', 'EN_ATTENTE');
GO


-- ============================================================
-- VUES DE CROISEMENT CNAV × SOURCES EXTERNES
-- ============================================================

-- 1. Pension CNAV vs inflation — pouvoir d'achat réel
CREATE VIEW rpt.v_PensionVsInflation AS
WITH base AS (
    SELECT
        a.annee,
        SUM(CASE WHEN g.code = 'T' THEN m.montant_euros END) AS montant_moyen_cnav,
        SUM(CASE WHEN g.code = 'H' THEN m.montant_euros END) AS montant_h,
        SUM(CASE WHEN g.code = 'F' THEN m.montant_euros END) AS montant_f
    FROM fact.Montants m
    JOIN dim.Annee     a ON a.annee_id      = m.annee_id
    JOIN dim.Genre     g ON g.genre_id      = m.genre_id
    JOIN dim.TypeDroit d ON d.type_droit_id = m.type_droit_id
    WHERE m.mesure = 'montant_global'
      AND d.code   = 'DROIT_DIRECT'
    GROUP BY a.annee
)
SELECT
    b.annee,
    b.montant_moyen_cnav,
    b.montant_h,
    b.montant_f,
    ie.valeur                               AS inflation_pct,
    -- Indice base 100 sur la première année disponible (calcul approximatif)
    ROUND(b.montant_moyen_cnav / NULLIF(
        (SELECT valeur / 100.0 + 1
         FROM ext.INSEE_IndicesEconomiques
         WHERE annee = b.annee AND indicateur = 'INFLATION_PCT'), 0), 2)
                                            AS montant_cnav_reel_approx
FROM base b
LEFT JOIN ext.INSEE_IndicesEconomiques ie
    ON ie.annee = b.annee AND ie.indicateur = 'INFLATION_PCT';
GO


-- 2. Effectifs CNAV vs pyramide INSEE — taux de retraite
CREATE VIEW rpt.v_TauxRetraiteVsPopulation AS
SELECT
    a.annee,
    g.libelle                                           AS genre,
    SUM(f.nb_retraites)                                 AS retraites_cnav,
    SUM(p.population)                                   AS population_60_plus,
    ROUND(
        100.0 * SUM(f.nb_retraites) / NULLIF(SUM(p.population), 0)
    , 1)                                                AS taux_retraite_pct
FROM fact.RetraitesEffectifs f
JOIN dim.Annee  a ON a.annee_id  = f.annee_id
JOIN dim.Genre  g ON g.genre_id  = f.genre_id
JOIN dim.CARSAT c ON c.carsat_id = f.carsat_id
LEFT JOIN ext.INSEE_PyramideAges p
    ON p.annee = a.annee
   AND p.genre_code = g.code
   AND p.age >= 60
WHERE c.code = 'TOTAL'
GROUP BY a.annee, g.libelle;
GO


-- 3. Détection de rupture — âge moyen vs réformes
CREATE VIEW rpt.v_AgeMoyenVsReformes AS
SELECT
    ag.annee,
    ag.genre,
    ag.type_droit,
    ag.age_moyen,
    r.nom                                   AS reforme,
    r.age_legal_avant,
    r.age_legal_apres,
    r.duree_cotis_avant,
    r.duree_cotis_apres,
    CASE WHEN r.reforme_id IS NOT NULL THEN 1 ELSE 0 END AS annee_reforme
FROM rpt.v_AgeMoyenAttribution ag
LEFT JOIN ext.COR_Reformes r ON r.annee = ag.annee;
GO


-- 4. Comparaison CNAV vs pension globale tous régimes (DREES)
CREATE VIEW rpt.v_CompaisonRegimes AS
SELECT
    a.annee,
    g.code                                          AS genre_code,
    -- CNAV
    MAX(CASE WHEN m.mesure = 'montant_global' AND dr.code = 'DROIT_DIRECT'
             THEN m.montant_euros END)              AS pension_base_cnav,
    -- Tous régimes DREES
    MAX(CASE WHEN dp.indicateur = 'PENSION_BRUTE_MOIS' AND dp.regime_id = 99
             THEN dp.valeur END)                    AS pension_tous_regimes_brut,
    -- Part CNAV dans la pension totale
    ROUND(
        100.0 * MAX(CASE WHEN m.mesure = 'montant_global' AND dr.code = 'DROIT_DIRECT'
                         THEN m.montant_euros END)
        / NULLIF(MAX(CASE WHEN dp.indicateur = 'PENSION_BRUTE_MOIS' AND dp.regime_id = 99
                          THEN dp.valeur * 12 END), 0)
    , 1)                                            AS part_cnav_pct
FROM fact.Montants m
JOIN dim.Annee     a  ON a.annee_id       = m.annee_id
JOIN dim.Genre     g  ON g.genre_id       = m.genre_id
JOIN dim.TypeDroit dr ON dr.type_droit_id = m.type_droit_id
LEFT JOIN ext.DREES_PensionsMultiRegimes dp
    ON dp.annee = a.annee AND dp.genre_code = g.code
WHERE g.code IN ('H','F','T')
GROUP BY a.annee, g.code;
GO


-- 5. Espérance de vie à la retraite (durée de retraite estimée)
CREATE VIEW rpt.v_DureeRetraiteEstimee AS
SELECT
    ag.annee,
    ag.genre,
    ag.age_moyen                                        AS age_depart,
    ev.esperance_annees                                 AS esperance_vie_a_60,
    ROUND(
        ev.esperance_annees - NULLIF(ag.age_moyen - 60, 0)
    , 1)                                                AS duree_retraite_estimee_ans,
    r.nom                                               AS derniere_reforme
FROM rpt.v_AgeMoyenAttribution ag
LEFT JOIN ext.INSEE_EsperanceVie ev
    ON ev.annee       = ag.annee
   AND ev.genre_code  = LEFT(ag.genre, 1)
   AND ev.age_reference = 60
   AND ev.type_mesure = 'conjoncturelle'
LEFT JOIN ext.COR_Reformes r
    ON r.annee = (
        SELECT MAX(annee) FROM ext.COR_Reformes
        WHERE annee <= ag.annee
    )
WHERE ag.type_droit = N'Droit direct (retraite personnelle)';
GO


-- 6. Projection CNAV vs scénarios COR
CREATE VIEW rpt.v_ProjectionVsCOR AS
SELECT
    a.annee,
    sc.code                                     AS scenario_cor,
    sc.libelle                                  AS scenario_libelle,
    -- Effectifs réels CNAV (si disponibles)
    SUM(re.nb_retraites)                        AS retraites_cnav_reel,
    -- Projection COR
    MAX(CASE WHEN cp.indicateur = 'NB_RETRAITES' THEN cp.valeur END) AS retraites_cor_proj,
    MAX(CASE WHEN cp.indicateur = 'DEPENSES_PCT_PIB' THEN cp.valeur END) AS depenses_pib_pct,
    MAX(CASE WHEN cp.indicateur = 'TAUX_REMPLACEMENT_NET' THEN cp.valeur END) AS taux_remplacement
FROM dim.Annee a
CROSS JOIN ext.COR_Scenarios sc
LEFT JOIN ext.COR_Projections cp
    ON cp.annee = a.annee AND cp.scenario_id = sc.scenario_id
LEFT JOIN fact.RetraitesEffectifs re
    ON re.annee_id = a.annee_id
LEFT JOIN dim.CARSAT c
    ON c.carsat_id = re.carsat_id AND c.code = 'TOTAL'
WHERE a.annee BETWEEN 2000 AND 2070
GROUP BY a.annee, sc.code, sc.libelle;
GO


-- 7. Vue synthèse multi-sources — tableau de bord principal
CREATE VIEW rpt.v_DashboardPrincipal AS
SELECT
    a.annee,
    -- Effectifs
    SUM(re.nb_retraites)                                AS retraites_total_cnav,
    -- Montant moyen
    MAX(CASE WHEN mo.mesure = 'montant_global'
              AND dr.code = 'DROIT_DIRECT'
              AND g.code  = 'T'
             THEN mo.montant_euros END)                 AS pension_moy_cnav,
    -- Âge moyen attribution
    MAX(CASE WHEN ag.mesure = 'age_moyen_attribution'
              AND ag.categorie_age_id IS NULL
              AND g.code = 'T'
             THEN ag.valeur END)                        AS age_moyen_depart,
    -- Inflation
    MAX(ie.valeur)                                      AS inflation_pct,
    -- Espérance de vie à 60 ans (F)
    MAX(CASE WHEN ev.genre_code = 'F' AND ev.age_reference = 60
             THEN ev.esperance_annees END)              AS esperance_vie_60_f,
    MAX(CASE WHEN ev.genre_code = 'H' AND ev.age_reference = 60
             THEN ev.esperance_annees END)              AS esperance_vie_60_h,
    -- Réforme éventuelle
    MAX(ref.nom)                                        AS reforme_annee
FROM dim.Annee a
LEFT JOIN fact.RetraitesEffectifs re ON re.annee_id = a.annee_id
LEFT JOIN dim.CARSAT c   ON c.carsat_id = re.carsat_id AND c.code = 'TOTAL'
LEFT JOIN fact.Montants mo ON mo.annee_id = a.annee_id
LEFT JOIN fact.Ages ag     ON ag.annee_id = a.annee_id
LEFT JOIN dim.Genre g      ON g.genre_id IN (mo.genre_id, re.genre_id, ag.genre_id)
LEFT JOIN dim.TypeDroit dr ON dr.type_droit_id = mo.type_droit_id
LEFT JOIN ext.INSEE_IndicesEconomiques ie
    ON ie.annee = a.annee AND ie.indicateur = 'INFLATION_PCT'
LEFT JOIN ext.INSEE_EsperanceVie ev
    ON ev.annee = a.annee AND ev.type_mesure = 'conjoncturelle'
LEFT JOIN ext.COR_Reformes ref ON ref.annee = a.annee
WHERE a.annee BETWEEN 1974 AND 2040
GROUP BY a.annee;
GO


-- ============================================================
-- RÉSUMÉ FINAL
-- ============================================================

SELECT
    s.name      AS [Schéma],
    t.name      AS [Table / Vue],
    CASE o.type WHEN 'U' THEN 'Table' WHEN 'V' THEN 'Vue' END AS [Type],
    p.rows      AS [Lignes]
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id = o.schema_id
LEFT JOIN sys.tables t ON t.object_id = o.object_id
LEFT JOIN sys.partitions p ON p.object_id = o.object_id AND p.index_id IN (0,1)
WHERE o.type IN ('U','V')
  AND s.name IN ('ext','rpt','meta')
ORDER BY s.name, o.type DESC, o.name;
GO
