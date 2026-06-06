# Architecture des Données

## 1. Sources de données

### 1.1 Source primaire — CNAV / API OpenDataSoft

**URL :** `https://data.assuranceretraite.fr/api/explore/v2.1/catalog/datasets`  
**Protocole :** REST/JSON, HTTPS, sans authentification  
**Licence :** Etalab Open License v2.0  
**Mise à jour :** annuelle (données N-1 publiées au 2e semestre)

| Thème | Dataset (nom fonctionnel) | Série | Enregistrements |
|---|---|---|---|
| Âges | Âge moyen au 31/12 | 1974 | ~52 |
| Âges | Âge moyen à l'attribution | — | ~63 |
| Assurés | Distribution des âges à l'attribution (tous droits) | — | ~2 518 |
| Assurés | Distribution des âges — droits dérivés | 1963 | ~2 499 |
| Assurés | Attributions annuelles par CARSAT | — | ~1 119 |
| Assurés | Attributions annuelles par type de droit | — | ~126 |
| Assurés | Retraités par CARSAT au 31/12 | 1960 | ~66 |
| Assurés | Retraités par genre au 31/12 | 1974 | ~104 |
| Assurés | Retraités par type de cotisation au 31/12 | — | ~66 |
| Assurés | Durée d'assurance (limitée/illimitée) | — | ~118 |
| Droits | Montant de base par catégorie de pension | — | ~756 |
| Droits | Montant de base — droits directs | — | ~189 |
| Droits | Montant global par genre | — | ~123 |
| Droits | Montant global par type de droit au 31/12 | — | ~116 |
| Droits | Montant global par type de droit et genre | — | ~378 |
| Droits | Montant global au 31/12 | 1960 | ~66 |
| Droits | Montant global — bénéficiaires minimum vieillesse | — | ~96 |
| Droits | Revenu annuel moyen des pensions attribuées | — | ~187 |

### 1.2 Sources secondaires

| Source | Organisme | Accès | Données clés |
|---|---|---|---|
| **INSEE** | Institut National de la Statistique | API BDM (token gratuit) + Excel | Pyramide des âges, espérance de vie, IPC, taux d'activité |
| **COR** | Conseil d'Orientation des Retraites | PDF/Excel sur cor-retraites.fr | Projections 2070, scénarios macro, historique des réformes |
| **DREES** | Direction de la Recherche, Études, Évaluation | Excel annuel (panorama DREES) | Pensions multi-régimes (AGIRC-ARRCO, MSA, SSI, FPE…) |

---

## 2. Flux de données

```
API OpenDataSoft          INSEE API BDM           COR Excel         DREES Excel
        │                       │                      │                  │
        ▼                       ▼                      ▼                  ▼
 fetch_data.py          fetch_external.py       fetch_external.py  fetch_external.py
        │                       │                      │                  │
        ▼                       ▼                      ▼                  ▼
data/raw/*.parquet      data/raw/external/      data/raw/external/  data/raw/external/
  (1 fichier/dataset)   insee_*.parquet         cor_*.parquet       drees_*.parquet
        │                       │                      │                  │
        └───────────────────────┴──────────────────────┴──────────────────┘
                                            │
                                            ▼
                                    clean_data.py
                                  (normalise + caste)
                                            │
                                            ▼
                             data/processed/*.parquet
                                            │
                              ┌─────────────┴──────────────┐
                              ▼                            ▼
                      fact.* SQL Server             ext.* SQL Server
                      (données CNAV)                (données externes)
                              │                            │
                              └─────────────┬──────────────┘
                                            ▼
                                   rpt.* (vues SQL)
                                   Croisements CNAV×INSEE×COR×DREES
                                            │
                                            ▼
                                   Notebooks Jupyter
                                   (analyses + modèles)
                                            │
                                            ▼
                                   reports/ (PNG, HTML, PDF)
```

---

## 3. Modèle relationnel SQL Server

### 3.1 Vue d'ensemble des schémas

| Schéma | Rôle | Tables |
|---|---|---|
| `dim` | Référentiels stables (dimensions) | 6 tables |
| `fact` | Mesures CNAV (faits) | 5 tables |
| `ext` | Données sources externes | 8 tables |
| `meta` | Catalogue API et logs d'ingestion | 3 tables |
| `rpt` | Vues analytiques croisées | 11 vues |

### 3.2 Diagramme entité-relation (simplifié)

```
dim.Annee (1960–2040)
    │
    ├──► fact.RetraitesEffectifs ──► dim.Genre
    │          │                ──► dim.CARSAT
    │          │                ──► dim.TypeCotisation
    │
    ├──► fact.Attributions ──► dim.Genre
    │          │           ──► dim.CARSAT
    │          │           ──► dim.TypeDroit
    │
    ├──► fact.Ages ──► dim.Genre
    │       │      ──► dim.TypeDroit
    │       │      ──► dim.CategorieAge (nullable)
    │
    ├──► fact.Montants ──► dim.Genre
    │          │        ──► dim.TypeDroit
    │
    ├──► fact.DureeAssurance ──► dim.Genre
    │                        ──► dim.TypeDroit
    │
    ├──► ext.INSEE_PyramideAges
    ├──► ext.INSEE_EsperanceVie
    ├──► ext.INSEE_IndicesEconomiques
    │
    ├──► ext.COR_Projections ──► ext.COR_Scenarios
    ├──► ext.COR_Reformes
    │
    └──► ext.DREES_PensionsMultiRegimes ──► ext.DREES_Regimes

meta.DatasetCatalog ──► meta.ImportLog
meta.SourcesExternesLog
```

### 3.3 Tables de dimensions

#### `dim.Annee`
| Colonne | Type | Description |
|---|---|---|
| annee_id | SMALLINT PK | Identifiant (= annee) |
| annee | SMALLINT | Année calendaire |
| decennie | SMALLINT | Décennie (1960, 1970…) |

Pré-remplie : 1960 → 2040 (81 lignes)

#### `dim.Genre`
| Code | Libellé |
|---|---|
| H | Hommes |
| F | Femmes |
| T | Total |

#### `dim.CARSAT`
18 caisses régionales + CNAV IDF + DOM + Total national

#### `dim.TypeDroit`
| Code | Libellé |
|---|---|
| DROIT_DIRECT | Retraite personnelle |
| DROIT_DERIVE | Réversion |
| DROITS_MIXTES | Directs et dérivés |
| TOTAL | Tous droits |

#### `dim.TypeCotisation`
Salarié privé, Fonctionnaire, Indépendant, Agricole, Autre, Total

#### `dim.CategorieAge`
Tranches quinquennales 55-59 ans → 95 ans et +

### 3.4 Tables de faits CNAV

Toutes les tables de faits partagent la même structure de clés :
- Clé surrogate `IDENTITY`
- Foreign keys vers les dimensions
- `source_dataset_id` → traçabilité vers `meta.DatasetCatalog`
- `date_import` → horodatage automatique

#### `fact.RetraitesEffectifs`
Effectif de retraités au 31 décembre par annee × genre × CARSAT × type de cotisation.

#### `fact.Attributions`
Nouveaux retraités dans l'année par annee × CARSAT × type de droit × genre.

#### `fact.Ages`
Âges moyens et distributions par annee × genre × type de droit.  
- `mesure` : `'age_moyen_31dec'` ou `'age_moyen_attribution'`
- `categorie_age_id` : NULL pour les moyennes, renseigné pour les distributions

#### `fact.Montants`
Montants de pensions par annee × genre × type de droit.  
- `mesure` : `'montant_base_direct'`, `'montant_global'`, `'revenu_annuel_moyen'`, `'montant_minimum_vieillesse'`
- `montant_euros` + `nb_beneficiaires`

#### `fact.DureeAssurance`
Durée d'assurance (limitée vs illimitée au taux plein) par annee × genre × type de droit.

### 3.5 Tables sources externes

#### `ext.INSEE_IndicesEconomiques`
Indicateurs macro : IPC, inflation (%), SMPT, taux d'activité 55-64 ans.  
**Pré-remplie** : inflation 2000-2024.

#### `ext.COR_Reformes`
Historique des réformes avec impact sur l'âge légal et la durée de cotisation.  
**Pré-remplie** : 6 réformes (1993 Balladur → 2023 Borne).

#### `ext.COR_Scenarios` + `ext.COR_Projections`
4 scénarios de croissance (0,7 % → 1,8 % PIB) × indicateurs (NB_RETRAITES, DEPENSES_PCT_PIB, TAUX_REMPLACEMENT_NET…)

#### `ext.DREES_Regimes` + `ext.DREES_PensionsMultiRegimes`
14 régimes de retraite (base, complémentaire, spéciaux).  
**Pré-remplie** : référentiel des régimes.

### 3.6 Vues reporting (`rpt`)

| Vue | Croisement | Usage |
|---|---|---|
| `v_EvolutionEffectifs` | CNAV × Annee × Genre | Courbe d'effectifs H/F |
| `v_EcartGenreMontants` | CNAV × Genre × TypeDroit | Écart H/F en € et % |
| `v_AgeMoyenAttribution` | CNAV × Annee × Genre | Âge de départ par type de droit |
| `v_AttributionsParCARSAT` | CNAV × CARSAT × Annee | Carte des attributions régionales |
| `v_PensionVsInflation` | CNAV × INSEE | Pouvoir d'achat réel des pensions |
| `v_TauxRetraiteVsPopulation` | CNAV × INSEE Pyramide | Taux de retraite vs population 60+ |
| `v_AgeMoyenVsReformes` | CNAV × COR Réformes | Détection de ruptures |
| `v_CompaisonRegimes` | CNAV × DREES | Part CNAV dans pension totale tous régimes |
| `v_DureeRetraiteEstimee` | CNAV × INSEE Espérance | Durée de retraite estimée |
| `v_ProjectionVsCOR` | CNAV × COR Projections | Réel vs 4 scénarios 2000-2070 |
| `v_DashboardPrincipal` | Multi-sources | Tableau de bord synthèse annuel |

---

## 4. Conventions de nommage

| Élément | Convention | Exemple |
|---|---|---|
| Tables SQL | PascalCase | `RetraitesEffectifs` |
| Colonnes SQL | snake_case | `nb_retraites`, `date_import` |
| Fichiers Parquet | kebab-case (nom dataset API) | `age-moyen-attribution.parquet` |
| Colonnes nettoyées | snake_case sans accent | `montant_euros`, `type_droit` |
| Vues reporting | préfixe `v_` + nom descriptif | `v_EcartGenreMontants` |

---

## 5. Politique de rétention des données

| Couche | Durée | Politique |
|---|---|---|
| `data/raw/` | Indéfinie | Immuable — archive des téléchargements |
| `data/processed/` | Jusqu'à prochain refresh | Régénérable depuis `raw/` |
| SQL Server fact.* | Indéfinie | Upsert à chaque import (clé unique sur les dimensions) |
| SQL Server ext.* | Mise à jour annuelle | Truncate + reload sur nouvelles publications |
| `reports/` | Indéfinie | Versionnement manuel recommandé |
