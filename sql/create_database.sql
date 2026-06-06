-- ============================================================
-- BASE DE DONNÉES : RetraitesOpenData
-- SQL Server 2022
-- Données ouvertes CNAV/CARSAT — data.assuranceretraite.fr
-- ============================================================

USE master;
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = N'RetraitesOpenData')
BEGIN
    ALTER DATABASE RetraitesOpenData SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE RetraitesOpenData;
END
GO

CREATE DATABASE RetraitesOpenData
    COLLATE French_CI_AS;
GO

ALTER DATABASE RetraitesOpenData SET RECOVERY SIMPLE;
GO

USE RetraitesOpenData;
GO

-- ============================================================
-- SCHÉMAS
-- ============================================================

CREATE SCHEMA dim;   -- Dimensions (référentiels)
GO
CREATE SCHEMA fact;  -- Tables de faits
GO
CREATE SCHEMA meta;  -- Catalogue & logs d'ingestion
GO
CREATE SCHEMA rpt;   -- Vues reporting
GO


-- ============================================================
-- DIMENSIONS
-- ============================================================

CREATE TABLE dim.Annee (
    annee_id    SMALLINT        NOT NULL,
    annee       SMALLINT        NOT NULL,
    decennie    SMALLINT        NOT NULL,
    CONSTRAINT PK_dim_Annee PRIMARY KEY (annee_id)
);
GO

-- Pré-remplir 1960 → 2040 (historique + horizon prédictif)
WITH cte AS (
    SELECT TOP 81 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) + 1959 AS yr
    FROM sys.all_objects
)
INSERT INTO dim.Annee (annee_id, annee, decennie)
SELECT CAST(yr AS SMALLINT),
       CAST(yr AS SMALLINT),
       CAST((yr / 10) * 10 AS SMALLINT)
FROM cte;
GO


CREATE TABLE dim.Genre (
    genre_id    TINYINT         NOT NULL,
    code        CHAR(1)         NOT NULL,   -- 'H', 'F', 'T' (total)
    libelle     NVARCHAR(20)    NOT NULL,
    CONSTRAINT PK_dim_Genre PRIMARY KEY (genre_id),
    CONSTRAINT UQ_dim_Genre_code UNIQUE (code)
);
INSERT INTO dim.Genre VALUES (1,'H',N'Hommes'), (2,'F',N'Femmes'), (3,'T',N'Total');
GO


CREATE TABLE dim.CARSAT (
    carsat_id   SMALLINT        NOT NULL,
    code        NVARCHAR(10)    NOT NULL,
    libelle     NVARCHAR(100)   NOT NULL,
    region      NVARCHAR(60)    NULL,
    CONSTRAINT PK_dim_CARSAT PRIMARY KEY (carsat_id),
    CONSTRAINT UQ_dim_CARSAT_code UNIQUE (code)
);
-- 15 caisses + CNAV IDF + CAVIMAC + total
INSERT INTO dim.CARSAT (carsat_id, code, libelle, region) VALUES
(1,  'CARSAT-AL',  N'CARSAT Alsace-Moselle',                N'Grand Est'),
(2,  'CARSAT-AQ',  N'CARSAT Aquitaine',                     N'Nouvelle-Aquitaine'),
(3,  'CARSAT-AV',  N'CARSAT Auvergne',                      N'Auvergne-Rhône-Alpes'),
(4,  'CARSAT-BN',  N'CARSAT Basse-Normandie',               N'Normandie'),
(5,  'CARSAT-BOU', N'CARSAT Bourgogne-Franche-Comté',       N'Bourgogne-Franche-Comté'),
(6,  'CARSAT-BR',  N'CARSAT Bretagne',                      N'Bretagne'),
(7,  'CARSAT-CE',  N'CARSAT Centre-Val de Loire',           N'Centre-Val de Loire'),
(8,  'CARSAT-HN',  N'CARSAT Haute-Normandie',               N'Normandie'),
(9,  'CARSAT-LAN', N'CARSAT Languedoc-Roussillon',          N'Occitanie'),
(10, 'CARSAT-LI',  N'CARSAT Limousin',                      N'Nouvelle-Aquitaine'),
(11, 'CARSAT-MR',  N'CARSAT Midi-Pyrénées',                 N'Occitanie'),
(12, 'CARSAT-NO',  N'CARSAT Nord-Picardie',                 N'Hauts-de-France'),
(13, 'CARSAT-NE',  N'CARSAT Nord-Est',                      N'Grand Est'),
(14, 'CARSAT-PL',  N'CARSAT Pays de la Loire',              N'Pays de la Loire'),
(15, 'CARSAT-RA',  N'CARSAT Rhône-Alpes',                   N'Auvergne-Rhône-Alpes'),
(16, 'CNAV-IDF',   N'CNAV Île-de-France',                   N'Île-de-France'),
(17, 'DOM',        N'Caisses Générale de Sécurité Sociale', N'DOM-TOM'),
(99, 'TOTAL',      N'France entière',                        NULL);
GO


CREATE TABLE dim.TypeDroit (
    type_droit_id   TINYINT         NOT NULL,
    code            NVARCHAR(20)    NOT NULL,
    libelle         NVARCHAR(80)    NOT NULL,
    categorie       NVARCHAR(20)    NOT NULL,   -- 'direct', 'derive', 'total'
    CONSTRAINT PK_dim_TypeDroit PRIMARY KEY (type_droit_id),
    CONSTRAINT UQ_dim_TypeDroit_code UNIQUE (code)
);
INSERT INTO dim.TypeDroit VALUES
(1,  'DROIT_DIRECT',    N'Droit direct (retraite personnelle)',  N'direct'),
(2,  'DROIT_DERIVE',    N'Droit dérivé (réversion)',             N'derive'),
(3,  'DROITS_MIXTES',   N'Droits directs et dérivés',            N'mixte'),
(4,  'TOTAL',           N'Tous droits confondus',                N'total');
GO


CREATE TABLE dim.TypeCotisation (
    type_cotisation_id  TINYINT         NOT NULL,
    code                NVARCHAR(20)    NOT NULL,
    libelle             NVARCHAR(80)    NOT NULL,
    CONSTRAINT PK_dim_TypeCotisation PRIMARY KEY (type_cotisation_id),
    CONSTRAINT UQ_dim_TypeCotisation_code UNIQUE (code)
);
INSERT INTO dim.TypeCotisation VALUES
(1, 'SALARIE',      N'Salarié du secteur privé'),
(2, 'FONCTIONNAIRE',N'Fonctionnaire'),
(3, 'INDEPENDANT',  N'Travailleur indépendant'),
(4, 'AGRICOLE',     N'Salarié agricole'),
(5, 'AUTRE',        N'Autre régime'),
(9, 'TOTAL',        N'Total tous régimes');
GO


CREATE TABLE dim.CategorieAge (
    categorie_age_id    SMALLINT        NOT NULL,
    borne_inf           TINYINT         NOT NULL,
    borne_sup           TINYINT         NOT NULL,
    libelle             NVARCHAR(20)    NOT NULL,
    CONSTRAINT PK_dim_CategorieAge PRIMARY KEY (categorie_age_id)
);
-- Tranches quinquennales 55-95
DECLARE @age TINYINT = 55, @id SMALLINT = 1;
WHILE @age <= 90
BEGIN
    INSERT INTO dim.CategorieAge VALUES
        (@id, @age, @age + 4, CONCAT(CAST(@age AS VARCHAR), '-', CAST(@age+4 AS VARCHAR), ' ans'));
    SET @age += 5; SET @id += 1;
END
INSERT INTO dim.CategorieAge VALUES (@id, 95, 99, N'95 ans et +');
GO


-- ============================================================
-- TABLES DE FAITS
-- ============================================================

-- Effectif total des retraités au 31/12
CREATE TABLE fact.RetraitesEffectifs (
    effectif_id         INT             NOT NULL IDENTITY(1,1),
    annee_id            SMALLINT        NOT NULL,
    genre_id            TINYINT         NOT NULL,
    carsat_id           SMALLINT        NOT NULL,
    type_cotisation_id  TINYINT         NOT NULL,
    nb_retraites        INT             NULL,
    source_dataset_id   INT             NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_fact_RetraitesEffectifs PRIMARY KEY (effectif_id),
    CONSTRAINT FK_fact_RE_annee     FOREIGN KEY (annee_id)           REFERENCES dim.Annee (annee_id),
    CONSTRAINT FK_fact_RE_genre     FOREIGN KEY (genre_id)           REFERENCES dim.Genre (genre_id),
    CONSTRAINT FK_fact_RE_carsat    FOREIGN KEY (carsat_id)          REFERENCES dim.CARSAT (carsat_id),
    CONSTRAINT FK_fact_RE_cotis     FOREIGN KEY (type_cotisation_id) REFERENCES dim.TypeCotisation (type_cotisation_id)
);
CREATE UNIQUE INDEX UQ_fact_RetraitesEffectifs
    ON fact.RetraitesEffectifs (annee_id, genre_id, carsat_id, type_cotisation_id);
GO


-- Attributions annuelles (nouveaux retraités dans l'année)
CREATE TABLE fact.Attributions (
    attribution_id      INT             NOT NULL IDENTITY(1,1),
    annee_id            SMALLINT        NOT NULL,
    carsat_id           SMALLINT        NOT NULL,
    type_droit_id       TINYINT         NOT NULL,
    genre_id            TINYINT         NOT NULL,
    nb_attributions     INT             NULL,
    source_dataset_id   INT             NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_fact_Attributions PRIMARY KEY (attribution_id),
    CONSTRAINT FK_fact_AT_annee     FOREIGN KEY (annee_id)       REFERENCES dim.Annee (annee_id),
    CONSTRAINT FK_fact_AT_carsat    FOREIGN KEY (carsat_id)      REFERENCES dim.CARSAT (carsat_id),
    CONSTRAINT FK_fact_AT_droit     FOREIGN KEY (type_droit_id)  REFERENCES dim.TypeDroit (type_droit_id),
    CONSTRAINT FK_fact_AT_genre     FOREIGN KEY (genre_id)       REFERENCES dim.Genre (genre_id)
);
CREATE UNIQUE INDEX UQ_fact_Attributions
    ON fact.Attributions (annee_id, carsat_id, type_droit_id, genre_id);
GO


-- Âges (moyens + distributions)
CREATE TABLE fact.Ages (
    age_id              INT             NOT NULL IDENTITY(1,1),
    annee_id            SMALLINT        NOT NULL,
    genre_id            TINYINT         NOT NULL,
    type_droit_id       TINYINT         NOT NULL,
    mesure              NVARCHAR(30)    NOT NULL,   -- 'age_moyen_31dec', 'age_moyen_attribution'
    categorie_age_id    SMALLINT        NULL,       -- NULL si valeur agrégée (âge moyen)
    valeur              DECIMAL(6,2)    NULL,       -- âge moyen ou nb de bénéficiaires dans la tranche
    source_dataset_id   INT             NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_fact_Ages PRIMARY KEY (age_id),
    CONSTRAINT FK_fact_AG_annee     FOREIGN KEY (annee_id)          REFERENCES dim.Annee (annee_id),
    CONSTRAINT FK_fact_AG_genre     FOREIGN KEY (genre_id)          REFERENCES dim.Genre (genre_id),
    CONSTRAINT FK_fact_AG_droit     FOREIGN KEY (type_droit_id)     REFERENCES dim.TypeDroit (type_droit_id),
    CONSTRAINT FK_fact_AG_catage    FOREIGN KEY (categorie_age_id)  REFERENCES dim.CategorieAge (categorie_age_id)
);
GO


-- Montants de pensions
CREATE TABLE fact.Montants (
    montant_id          INT             NOT NULL IDENTITY(1,1),
    annee_id            SMALLINT        NOT NULL,
    genre_id            TINYINT         NOT NULL,
    type_droit_id       TINYINT         NOT NULL,
    mesure              NVARCHAR(40)    NOT NULL,
        -- 'montant_base_direct', 'montant_global', 'revenu_annuel_moyen',
        -- 'montant_minimum_vieillesse'
    montant_euros       DECIMAL(12,2)   NULL,
    nb_beneficiaires    INT             NULL,
    source_dataset_id   INT             NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_fact_Montants PRIMARY KEY (montant_id),
    CONSTRAINT FK_fact_MO_annee     FOREIGN KEY (annee_id)      REFERENCES dim.Annee (annee_id),
    CONSTRAINT FK_fact_MO_genre     FOREIGN KEY (genre_id)      REFERENCES dim.Genre (genre_id),
    CONSTRAINT FK_fact_MO_droit     FOREIGN KEY (type_droit_id) REFERENCES dim.TypeDroit (type_droit_id)
);
GO


-- Durée d'assurance
CREATE TABLE fact.DureeAssurance (
    duree_id            INT             NOT NULL IDENTITY(1,1),
    annee_id            SMALLINT        NOT NULL,
    genre_id            TINYINT         NOT NULL,
    type_droit_id       TINYINT         NOT NULL,
    limitee             BIT             NOT NULL,   -- 1 = durée limitée au taux plein, 0 = illimitée
    nb_retraites        INT             NULL,
    duree_moyenne_trim  DECIMAL(6,1)    NULL,       -- trimestres
    source_dataset_id   INT             NULL,
    date_import         DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_fact_DureeAssurance PRIMARY KEY (duree_id),
    CONSTRAINT FK_fact_DA_annee     FOREIGN KEY (annee_id)      REFERENCES dim.Annee (annee_id),
    CONSTRAINT FK_fact_DA_genre     FOREIGN KEY (genre_id)      REFERENCES dim.Genre (genre_id),
    CONSTRAINT FK_fact_DA_droit     FOREIGN KEY (type_droit_id) REFERENCES dim.TypeDroit (type_droit_id)
);
GO


-- ============================================================
-- MÉTADONNÉES & INGESTION
-- ============================================================

CREATE TABLE meta.DatasetCatalog (
    dataset_id      INT             NOT NULL IDENTITY(1,1),
    dataset_api_id  NVARCHAR(120)   NOT NULL,   -- identifiant OpenDataSoft
    titre           NVARCHAR(200)   NULL,
    theme           NVARCHAR(60)    NULL,
    serie_depuis    SMALLINT        NULL,
    nb_records_api  INT             NULL,
    description     NVARCHAR(MAX)   NULL,
    date_decouverte DATETIME2(0)    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_meta_DatasetCatalog PRIMARY KEY (dataset_id),
    CONSTRAINT UQ_meta_DatasetCatalog_apiid UNIQUE (dataset_api_id)
);
GO

CREATE TABLE meta.ImportLog (
    log_id              INT             NOT NULL IDENTITY(1,1),
    dataset_id          INT             NOT NULL,
    debut_import        DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
    fin_import          DATETIME2(3)    NULL,
    nb_lignes_brutes    INT             NULL,
    nb_lignes_chargees  INT             NULL,
    statut              NVARCHAR(20)    NOT NULL DEFAULT N'EN_COURS',
        -- 'EN_COURS', 'SUCCES', 'ERREUR', 'PARTIEL'
    message_erreur      NVARCHAR(MAX)   NULL,
    CONSTRAINT PK_meta_ImportLog PRIMARY KEY (log_id),
    CONSTRAINT FK_meta_IL_dataset FOREIGN KEY (dataset_id) REFERENCES meta.DatasetCatalog (dataset_id)
);
GO


-- ============================================================
-- VUES REPORTING
-- ============================================================

-- Évolution des effectifs retraités (total France)
CREATE VIEW rpt.v_EvolutionEffectifs AS
SELECT
    a.annee,
    g.libelle                               AS genre,
    SUM(f.nb_retraites)                     AS nb_retraites
FROM fact.RetraitesEffectifs f
JOIN dim.Annee  a ON a.annee_id  = f.annee_id
JOIN dim.Genre  g ON g.genre_id  = f.genre_id
JOIN dim.CARSAT c ON c.carsat_id = f.carsat_id
WHERE c.code = 'TOTAL'
GROUP BY a.annee, g.libelle;
GO

-- Écart H/F sur les montants globaux
CREATE VIEW rpt.v_EcartGenreMontants AS
SELECT
    a.annee,
    td.libelle                                              AS type_droit,
    MAX(CASE WHEN g.code = 'H' THEN m.montant_euros END)   AS montant_hommes,
    MAX(CASE WHEN g.code = 'F' THEN m.montant_euros END)   AS montant_femmes,
    MAX(CASE WHEN g.code = 'H' THEN m.montant_euros END)
      - MAX(CASE WHEN g.code = 'F' THEN m.montant_euros END) AS ecart_hf,
    CASE
        WHEN MAX(CASE WHEN g.code = 'H' THEN m.montant_euros END) > 0
        THEN ROUND(
            100.0 * (MAX(CASE WHEN g.code = 'H' THEN m.montant_euros END)
                     - MAX(CASE WHEN g.code = 'F' THEN m.montant_euros END))
            / MAX(CASE WHEN g.code = 'H' THEN m.montant_euros END), 1)
        ELSE NULL
    END                                                     AS ecart_pct
FROM fact.Montants m
JOIN dim.Annee      a  ON a.annee_id      = m.annee_id
JOIN dim.Genre      g  ON g.genre_id      = m.genre_id
JOIN dim.TypeDroit  td ON td.type_droit_id = m.type_droit_id
WHERE m.mesure = 'montant_global'
  AND g.code IN ('H','F')
GROUP BY a.annee, td.libelle;
GO

-- Âge moyen d'attribution par année
CREATE VIEW rpt.v_AgeMoyenAttribution AS
SELECT
    a.annee,
    g.libelle   AS genre,
    td.libelle  AS type_droit,
    f.valeur    AS age_moyen
FROM fact.Ages f
JOIN dim.Annee     a  ON a.annee_id       = f.annee_id
JOIN dim.Genre     g  ON g.genre_id       = f.genre_id
JOIN dim.TypeDroit td ON td.type_droit_id = f.type_droit_id
WHERE f.mesure = 'age_moyen_attribution'
  AND f.categorie_age_id IS NULL;
GO

-- Attributions par CARSAT (dernière année disponible)
CREATE VIEW rpt.v_AttributionsParCARSAT AS
SELECT
    c.libelle   AS carsat,
    c.region,
    a.annee,
    td.libelle  AS type_droit,
    SUM(f.nb_attributions) AS nb_attributions
FROM fact.Attributions f
JOIN dim.Annee     a  ON a.annee_id       = f.annee_id
JOIN dim.CARSAT    c  ON c.carsat_id      = f.carsat_id
JOIN dim.TypeDroit td ON td.type_droit_id = f.type_droit_id
WHERE c.code <> 'TOTAL'
GROUP BY c.libelle, c.region, a.annee, td.libelle;
GO


-- ============================================================
-- INDEXES COMPLÉMENTAIRES
-- ============================================================

CREATE INDEX IX_fact_Montants_annee_mesure   ON fact.Montants        (annee_id, mesure);
CREATE INDEX IX_fact_Ages_annee_mesure        ON fact.Ages            (annee_id, mesure);
CREATE INDEX IX_fact_Attributions_annee_carsat ON fact.Attributions   (annee_id, carsat_id);
CREATE INDEX IX_meta_ImportLog_statut          ON meta.ImportLog      (statut, debut_import);
GO


-- ============================================================
-- RÉSUMÉ
-- ============================================================

SELECT
    s.name          AS [Schéma],
    t.name          AS [Table],
    p.rows          AS [Lignes init]
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)
ORDER BY s.name, t.name;
GO
