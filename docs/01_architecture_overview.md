# Architecture Overview — Retraites OpenData

## 1. Contexte et objectifs

### Problématique

Le système de retraite français produit chaque année plusieurs dizaines de milliers de publications statistiques dispersées entre différentes sources publiques (CNAV, INSEE, COR, DREES). Il n'existe pas de plateforme consolidée permettant de croiser ces données, d'identifier des tendances et de projeter leur évolution.

### Objectifs du projet

| Priorité | Objectif | Horizon |
|---|---|---|
| P0 | Centraliser les données ouvertes CNAV/CARSAT dans une base relationnelle | Immédiat |
| P1 | Produire des statistiques descriptives (effectifs, montants, âges, écarts H/F) | Court terme |
| P2 | Enrichir avec sources INSEE, COR, DREES | Court terme |
| P3 | Construire des modèles prédictifs (ARIMA, Prophet, régression) | Moyen terme |
| P4 | Générer des rapports HTML/PDF exportables | Moyen terme |

### Périmètre des données

- **Source primaire :** API OpenDataSoft — `data.assuranceretraite.fr` (18 datasets, licence Etalab Open License v2.0)
- **Sources secondaires :** INSEE, COR, DREES (données publiques téléchargeables)
- **Période couverte :** 1960 → présent (selon dataset) + projections jusqu'à 2070
- **Maille géographique :** France entière + 17 CARSAT/CNAV régionales

---

## 2. Vue d'ensemble du système

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SOURCES DE DONNÉES                                 │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────┐  ┌─────────┐  ┌────────────────┐  │
│  │ data.assuranceretraite│  │  INSEE   │  │   COR   │  │    DREES       │  │
│  │   .fr  (API REST)    │  │ API BDM  │  │ (Excel) │  │   (Excel)      │  │
│  │   18 datasets        │  │ + Excel  │  │         │  │                │  │
│  └──────────┬───────────┘  └────┬─────┘  └────┬────┘  └───────┬────────┘  │
└─────────────┼────────────────────┼─────────────┼───────────────┼───────────┘
              │                    │             │               │
              ▼                    ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COUCHE INGESTION (Python)                            │
│                                                                             │
│   src/fetch_data.py          src/fetch_external.py                         │
│   (OpenDataSoft → Parquet)   (INSEE/COR/DREES → Parquet)                   │
│                                                                             │
│   data/raw/*.parquet                                                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COUCHE NETTOYAGE (Python)                              │
│                                                                             │
│   src/clean_data.py                                                         │
│   (normalisation colonnes, cast types, déduplication)                      │
│                                                                             │
│   data/processed/*.parquet                                                  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COUCHE PERSISTANCE (SQL Server 2022)                     │
│                                                                             │
│   Base : RetraitesOpenData                                                  │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │  dim.*       │ │  fact.*      │ │  ext.*       │ │  rpt.*           │  │
│  │  Dimensions  │ │  Faits CNAV  │ │  Sources ext.│ │  Vues reporting  │  │
│  │  (référentiels)│ │            │ │  INSEE/COR   │ │  (croisements)   │  │
│  └──────────────┘ └──────────────┘ │  /DREES      │ └──────────────────┘  │
│                                    └──────────────┘                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COUCHE ANALYSE (Jupyter)                               │
│                                                                             │
│  01_exploration.ipynb     02_descriptive_stats.ipynb                       │
│  03_predictive_models.ipynb  04_regional_analysis.ipynb                    │
│                                                                             │
│  src/models.py (ARIMA, Prophet)  src/visualize.py (matplotlib, plotly)     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COUCHE DIFFUSION                                    │
│                                                                             │
│   reports/    (PNG, HTML, PDF exportés depuis les notebooks)               │
│   Jupyter Lab accessible sur http://WWDBA01-D01.groupesifa.com:8888        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Principes d'architecture

### 3.1 Séparation des couches
Chaque couche a une responsabilité unique et une interface claire :
- **Ingestion** → fichiers Parquet bruts (immuables une fois écrits)
- **Nettoyage** → fichiers Parquet traités (reproductibles depuis les bruts)
- **Persistance** → SQL Server (source de vérité pour les analyses)
- **Analyse** → notebooks lisibles par des non-développeurs

### 3.2 Reproducibilité
Tout le pipeline est rejouable depuis zéro avec les deux commandes :
```
python src/fetch_data.py
python src/clean_data.py
```
Les données brutes sont en Parquet (format colonnaire, compression automatique, schéma embarqué).

### 3.3 Sécurité — aucune credential en clair
Aucun mot de passe ne figure dans le code, les fichiers de configuration versionnés, ou les notebooks. Tous les secrets transitent par **Azure Key Vault** (`sifa-vault1`) via `DefaultAzureCredential`.

### 3.4 Ouverture aux enrichissements
Le schéma SQL est conçu pour accueillir de nouveaux datasets sans migration : les tables de faits n'ont pas de contraintes sur les colonnes métier, et le système de clés surrogate (`IDENTITY`) permet l'ajout de nouvelles sources sans conflit.

---

## 4. Choix technologiques

| Composant | Choix | Justification |
|---|---|---|
| Langage | Python 3.10 | Écosystème data science, compatibilité Prophet/statsmodels |
| Format stockage intermédiaire | Apache Parquet | Colonnaire, compressé, schéma auto, compatible pandas |
| Base de données | SQL Server 2022 | Déjà en place sur WWDBA01-D01, ODBC natif Windows |
| ORM / connecteur | SQLAlchemy 2 + pyodbc | Abstraction base, bulk insert `fast_executemany` |
| Secrets | Azure Key Vault | Déjà utilisé dans l'infra SIFA |
| Auth credentials | DefaultAzureCredential | Chaîne automatique SP → Managed Identity → Az PowerShell |
| Série temporelle | ARIMA (statsmodels) + Prophet (Meta) | Complémentaires : ARIMA précis sur courte série, Prophet robuste aux tendances et réformes |
| Visualisation | matplotlib + plotly | matplotlib pour exports statiques, plotly pour notebooks interactifs |

---

## 5. Contraintes et hypothèses

| Contrainte | Impact | Mitigation |
|---|---|---|
| API CNAV publique sans authentification | Pas de garantie SLA | Mise en cache Parquet locale |
| Données INSEE/COR/DREES non disponibles via API unifiée | Téléchargement manuel Excel | Script `fetch_external.py` pour automatisation partielle |
| SQL Server en mode `sa` | Risque sécurité en production | Créer un compte applicatif dédié (voir `sql/create_service_principal.ps1`) |
| Conditional Access Azure bloque la création SP depuis ce serveur | SP non créé automatiquement | Script prêt, à exécuter depuis réseau interne par un admin AD |
| Windows Server 2019 (pas de WSL2 natif) | Pas de Linux tools | Tous les scripts prévoient PowerShell |

---

## 6. Index des documents

| Document | Contenu |
|---|---|
| [02_data_architecture.md](02_data_architecture.md) | Schéma SQL, flux de données, modèle relationnel |
| [03_application_architecture.md](03_application_architecture.md) | Modules Python, notebooks, dépendances |
| [04_infrastructure.md](04_infrastructure.md) | SQL Server, Azure, réseau, variables d'environnement |
| [05_security.md](05_security.md) | Key Vault, Service Principal, gestion des secrets |
| [06_installation.md](06_installation.md) | Guide d'installation complet pas à pas |
| [07_operations.md](07_operations.md) | Redémarrage, maintenance, troubleshooting |
| [08_data_dictionary.md](08_data_dictionary.md) | Dictionnaire complet des tables et colonnes |
