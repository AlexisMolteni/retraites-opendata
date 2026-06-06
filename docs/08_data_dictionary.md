# Dictionnaire des Données

> Référence complète de toutes les tables, colonnes et valeurs codifiées de la base `RetraitesOpenData`.

---

## Schéma `dim` — Dimensions

### `dim.Annee`

| Colonne | Type | Nullable | Description |
|---|---|---|---|
| `annee_id` | SMALLINT | NO | Clé primaire (= annee) |
| `annee` | SMALLINT | NO | Année calendaire (1960–2040) |
| `decennie` | SMALLINT | NO | Décennie arrondie (1960, 1970…) |

**Valeurs :** 1960 à 2040. Les années > présent sont réservées aux projections.

---

### `dim.Genre`

| genre_id | code | libelle |
|---|---|---|
| 1 | H | Hommes |
| 2 | F | Femmes |
| 3 | T | Total (hommes + femmes confondus) |

---

### `dim.CARSAT`

| Colonne | Type | Description |
|---|---|---|
| `carsat_id` | SMALLINT | Clé primaire |
| `code` | NVARCHAR(10) | Code court (ex: `CARSAT-AL`, `CNAV-IDF`, `TOTAL`) |
| `libelle` | NVARCHAR(100) | Nom complet de la caisse |
| `region` | NVARCHAR(60) | Région administrative (nullable pour TOTAL) |

**Valeurs importantes :**
- `TOTAL` (carsat_id=99) : agrégation France entière — utiliser pour les statistiques nationales
- `CNAV-IDF` (carsat_id=16) : Caisse Nationale d'Assurance Vieillesse d'Île-de-France
- `DOM` (carsat_id=17) : Caisses Générales de Sécurité Sociale (Guadeloupe, Martinique, Guyane, Réunion)

---

### `dim.TypeDroit`

| type_droit_id | code | libelle | categorie |
|---|---|---|---|
| 1 | DROIT_DIRECT | Droit direct (retraite personnelle) | direct |
| 2 | DROIT_DERIVE | Droit dérivé (réversion) | derive |
| 3 | DROITS_MIXTES | Droits directs et dérivés | mixte |
| 4 | TOTAL | Tous droits confondus | total |

**Glossaire :**
- **Droit direct** : pension attribuée à l'assuré lui-même en fonction de sa carrière
- **Droit dérivé (réversion)** : pension attribuée au conjoint survivant, représentant 54 % de la pension du défunt
- **Droits mixtes** : bénéficiaires touchant à la fois une pension personnelle ET une pension de réversion

---

### `dim.TypeCotisation`

| type_cotisation_id | code | libelle |
|---|---|---|
| 1 | SALARIE | Salarié du secteur privé |
| 2 | FONCTIONNAIRE | Fonctionnaire |
| 3 | INDEPENDANT | Travailleur indépendant (ex-RSI/SSI) |
| 4 | AGRICOLE | Salarié agricole (MSA) |
| 5 | AUTRE | Autre régime |
| 9 | TOTAL | Total tous régimes |

---

### `dim.CategorieAge`

Tranches d'âge quinquennales utilisées pour les distributions.

| categorie_age_id | borne_inf | borne_sup | libelle |
|---|---|---|---|
| 1 | 55 | 59 | 55-59 ans |
| 2 | 60 | 64 | 60-64 ans |
| 3 | 65 | 69 | 65-69 ans |
| … | … | … | … |
| 9 | 95 | 99 | 95 ans et + |

---

## Schéma `fact` — Faits CNAV

### Colonnes communes à toutes les tables de faits

| Colonne | Type | Description |
|---|---|---|
| `*_id` | INT IDENTITY | Clé surrogate auto-incrémentée |
| `annee_id` | SMALLINT FK | Référence `dim.Annee.annee_id` |
| `source_dataset_id` | INT FK | Référence `meta.DatasetCatalog.dataset_id` (traçabilité) |
| `date_import` | DATETIME2(0) | Horodatage UTC de l'insertion (défaut : `SYSUTCDATETIME()`) |

---

### `fact.RetraitesEffectifs`

Effectif de retraités au 31 décembre.

| Colonne | Type | Description |
|---|---|---|
| `effectif_id` | INT | Clé primaire |
| `annee_id` | SMALLINT | Année d'observation |
| `genre_id` | TINYINT | Genre |
| `carsat_id` | SMALLINT | Caisse régionale ou TOTAL |
| `type_cotisation_id` | TINYINT | Type de régime de cotisation |
| `nb_retraites` | INT | Effectif de retraités au 31/12 |

**Contrainte d'unicité :** `(annee_id, genre_id, carsat_id, type_cotisation_id)`

**Exemple de requête :**
```sql
-- Évolution nationale des effectifs H/F depuis 1974
SELECT a.annee, g.libelle, SUM(f.nb_retraites) AS effectif
FROM fact.RetraitesEffectifs f
JOIN dim.Annee a ON a.annee_id = f.annee_id
JOIN dim.Genre g ON g.genre_id = f.genre_id
JOIN dim.CARSAT c ON c.carsat_id = f.carsat_id
WHERE c.code = 'TOTAL'
GROUP BY a.annee, g.libelle
ORDER BY a.annee;
```

---

### `fact.Attributions`

Nouveaux retraités dans l'année (flux d'entrée).

| Colonne | Type | Description |
|---|---|---|
| `attribution_id` | INT | Clé primaire |
| `annee_id` | SMALLINT | Année des attributions |
| `carsat_id` | SMALLINT | Caisse ayant attribué la pension |
| `type_droit_id` | TINYINT | Type de droit attribué |
| `genre_id` | TINYINT | Genre |
| `nb_attributions` | INT | Nombre de nouvelles pensions attribuées dans l'année |

**Contrainte d'unicité :** `(annee_id, carsat_id, type_droit_id, genre_id)`

---

### `fact.Ages`

Âges moyens et distributions d'âge à l'attribution ou au 31/12.

| Colonne | Type | Description |
|---|---|---|
| `age_id` | INT | Clé primaire |
| `annee_id` | SMALLINT | Année d'observation |
| `genre_id` | TINYINT | Genre |
| `type_droit_id` | TINYINT | Type de droit |
| `mesure` | NVARCHAR(30) | Type de mesure (voir valeurs ci-dessous) |
| `categorie_age_id` | SMALLINT | NULL pour les moyennes, référence dim.CategorieAge pour les distributions |
| `valeur` | DECIMAL(6,2) | Âge moyen (années) ou effectif dans la tranche |

**Valeurs de `mesure` :**

| Valeur | Description |
|---|---|
| `age_moyen_31dec` | Âge moyen des retraités au 31 décembre |
| `age_moyen_attribution` | Âge moyen lors de l'attribution de la pension |

---

### `fact.Montants`

Montants de pensions par catégorie.

| Colonne | Type | Description |
|---|---|---|
| `montant_id` | INT | Clé primaire |
| `annee_id` | SMALLINT | Année d'observation |
| `genre_id` | TINYINT | Genre |
| `type_droit_id` | TINYINT | Type de droit |
| `mesure` | NVARCHAR(40) | Type de montant (voir valeurs ci-dessous) |
| `montant_euros` | DECIMAL(12,2) | Montant en euros |
| `nb_beneficiaires` | INT | Nombre de bénéficiaires concernés |

**Valeurs de `mesure` :**

| Valeur | Description | Périodicité |
|---|---|---|
| `montant_base_direct` | Montant de pension de base, droits directs | Mensuel ou annuel selon dataset |
| `montant_global` | Montant global toutes catégories | — |
| `revenu_annuel_moyen` | Revenu annuel moyen des pensions nouvellement attribuées | Annuel |
| `montant_minimum_vieillesse` | Montant pour bénéficiaires du minimum vieillesse (ASPA) | — |

---

### `fact.DureeAssurance`

Durée d'assurance validée par les retraités.

| Colonne | Type | Description |
|---|---|---|
| `duree_id` | INT | Clé primaire |
| `annee_id` | SMALLINT | Année d'observation |
| `genre_id` | TINYINT | Genre |
| `type_droit_id` | TINYINT | Type de droit |
| `limitee` | BIT | 1 = durée limitée au taux plein (décote) / 0 = durée illimitée (surcote ou exacte) |
| `nb_retraites` | INT | Effectif dans cette catégorie |
| `duree_moyenne_trim` | DECIMAL(6,1) | Durée moyenne en trimestres |

**Note :** La durée de cotisation requise pour le taux plein est passée de 37,5 ans (150 trim.) à 43 ans (172 trim.) selon les générations (réformes 1993 → 2023).

---

## Schéma `ext` — Sources Externes

### `ext.INSEE_PyramideAges`

| Colonne | Type | Description |
|---|---|---|
| `annee` | SMALLINT | Année (au 1er janvier) |
| `age` | TINYINT | Âge révolu (0 à 99+) |
| `genre_code` | CHAR(1) | H / F / T |
| `population` | BIGINT | Effectif de la population |

---

### `ext.INSEE_EsperanceVie`

| Colonne | Type | Description |
|---|---|---|
| `annee` | SMALLINT | Année d'observation |
| `genre_code` | CHAR(1) | H / F / T |
| `age_reference` | TINYINT | 0 (naissance), 60, 62, 64, 65, 67 |
| `esperance_annees` | DECIMAL(5,2) | Nombre d'années de vie restantes |
| `type_mesure` | NVARCHAR(20) | `conjoncturelle` ou `du_moment` |

---

### `ext.INSEE_IndicesEconomiques`

| Valeur `indicateur` | Unité | Description |
|---|---|---|
| `IPC_BASE100_1998` | Indice | Indice des prix à la consommation |
| `INFLATION_PCT` | % | Taux d'inflation annuel |
| `SMPT_EUROS` | € | Salaire Moyen Par Tête |
| `TAUX_ACTIVITE_55_64` | % | Taux d'activité des 55-64 ans |
| `TAUX_ACTIVITE_60_64` | % | Taux d'activité des 60-64 ans |
| `PIB_HABITANT` | € | PIB par habitant |

**Données pré-remplies :** inflation 2000–2024.

---

### `ext.COR_Reformes`

| Colonne | Type | Description |
|---|---|---|
| `annee` | SMALLINT | Année de la réforme |
| `nom` | NVARCHAR(100) | Nom de la réforme |
| `age_legal_avant` / `_apres` | TINYINT | Âge légal de départ avant/après réforme |
| `age_taux_plein_avant` / `_apres` | TINYINT | Âge du taux plein automatique |
| `duree_cotis_avant` / `_apres` | DECIMAL(4,1) | Durée de cotisation requise (années) |
| `impact_attendu` | NVARCHAR(200) | Description synthétique de l'impact |

**Réformes enregistrées :** 1993 (Balladur), 2003 (Fillon), 2007 (régimes spéciaux), 2010 (Woerth), 2014 (Touraine), 2023 (Borne).

---

### `ext.COR_Scenarios`

| scenario_id | code | croissance_pib |
|---|---|---|
| 1 | PESSIMISTE | 0,7 %/an |
| 2 | CENTRAL_BAS | 1,0 %/an |
| 3 | CENTRAL_HAUT | 1,3 %/an (référence) |
| 4 | OPTIMISTE | 1,8 %/an |

---

### `ext.DREES_Regimes`

| Colonne | Type | Description |
|---|---|---|
| `code` | NVARCHAR(20) | Code court (ex: `CNAV`, `AGIRC_ARRCO`) |
| `type_regime` | NVARCHAR(20) | `base`, `complementaire`, `special`, `total` |

**Régimes enregistrés :** CNAV, AGIRC-ARRCO, IRCANTEC, CNRACL, FPE, MSA (salariés + exploitants), SSI, CNAVPL, CNBF (avocats), SNCF, RATP, CNIEG, TOUS_REGIMES.

---

## Schéma `meta` — Métadonnées

### `meta.DatasetCatalog`

| Colonne | Description |
|---|---|
| `dataset_api_id` | Identifiant unique côté API OpenDataSoft |
| `titre` | Titre humain du dataset |
| `theme` | Thème fonctionnel (Âges, Assurés, Droits) |
| `serie_depuis` | Première année disponible dans la série |
| `nb_records_api` | Nombre d'enregistrements retourné par l'API |

---

### `meta.ImportLog`

Traçabilité de chaque ingestion.

| Valeur `statut` | Signification |
|---|---|
| `EN_COURS` | Import en cours d'exécution |
| `SUCCES` | Import terminé sans erreur |
| `PARTIEL` | Import partiel (certaines lignes rejetées) |
| `ERREUR` | Import échoué (voir `message_erreur`) |

---

## Vues `rpt` — Reporting

Toutes les vues du schéma `rpt` sont documentées dans [02_data_architecture.md](02_data_architecture.md#36-vues-reporting-rpt).

### Exemple d'utilisation du dashboard principal

```sql
SELECT
    annee,
    retraites_total_cnav,
    pension_moy_cnav,
    age_moyen_depart,
    inflation_pct,
    esperance_vie_60_f,
    esperance_vie_60_h,
    reforme_annee
FROM rpt.v_DashboardPrincipal
WHERE annee BETWEEN 1990 AND 2030
ORDER BY annee;
```

---

## Glossaire métier

| Terme | Définition |
|---|---|
| **CARSAT** | Caisse d'Assurance Retraite et de la Santé Au Travail — gère les retraites et la prévention des risques professionnels dans chaque région |
| **CNAV** | Caisse Nationale d'Assurance Vieillesse — organisme central du régime général |
| **Droit direct** | Pension calculée sur la propre carrière de l'assuré |
| **Droit dérivé (réversion)** | Pension versée au conjoint survivant (54 % de la pension du défunt) |
| **Taux plein** | Taux de liquidation maximal de la pension (50 % du salaire annuel moyen) |
| **Décote** | Réduction appliquée si la durée de cotisation est insuffisante au moment du départ |
| **Surcote** | Majoration accordée pour les trimestres cotisés au-delà du taux plein |
| **ASPA** | Allocation de Solidarité aux Personnes Âgées (ex-minimum vieillesse) |
| **Trimestre** | Unité de mesure de la durée d'assurance (4 trimestres = 1 an) |
| **Âge légal** | Âge minimal pour liquider sa retraite (64 ans depuis 2023) |
| **Âge du taux plein automatique** | Âge auquel la décote disparaît quelle que soit la durée cotisée (67 ans) |
| **COR** | Conseil d'Orientation des Retraites — produit des projections financières du système |
| **DREES** | Direction de la Recherche, des Études, de l'Évaluation et des Statistiques |
| **AGIRC-ARRCO** | Régime complémentaire obligatoire des salariés du secteur privé |
| **Prophet** | Bibliothèque de prévision de séries temporelles développée par Meta, robuste aux changements de tendance |
| **ARIMA** | AutoRegressive Integrated Moving Average — modèle statistique classique de séries temporelles |
