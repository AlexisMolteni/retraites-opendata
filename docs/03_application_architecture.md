# Architecture Applicative

## 1. Structure du projet

```
retraites-opendata/
│
├── data/
│   ├── raw/                    # Parquet bruts — 1 fichier par dataset API
│   │   └── external/           # Parquet sources externes (INSEE/COR/DREES)
│   └── processed/              # Parquet nettoyés (régénérables)
│
├── docs/                       # Documentation architecture (ce dossier)
│
├── notebooks/
│   ├── 01_exploration.ipynb    # Discovery des datasets, qualité
│   ├── 02_descriptive_stats.ipynb  # Statistiques descriptives, visualisations
│   ├── 03_predictive_models.ipynb  # ARIMA, Prophet, régression
│   └── 04_regional_analysis.ipynb  # Clustering et projection CARSAT
│
├── reports/                    # Exports générés (PNG, HTML, PDF)
│
├── scripts/
│   └── setup_credentials.ps1        # Setup one-time : écrit AZURE_CLIENT_SECRET dans le registre
│
├── sql/
│   ├── create_database.sql          # DDL base RetraitesOpenData
│   ├── create_enrichissements.sql   # DDL sources externes + vues croisées
│   └── create_service_principal.ps1 # Script création SP Azure AD (admin, réseau interne)
│
├── src/
│   ├── __init__.py
│   ├── fetch_data.py       # Ingestion API CNAV OpenDataSoft
│   ├── fetch_external.py   # Ingestion INSEE / COR / DREES
│   ├── clean_data.py       # Nettoyage et normalisation
│   ├── models.py           # Modèles prédictifs
│   ├── visualize.py        # Fonctions de visualisation
│   ├── vault.py            # Accès Azure Key Vault
│   └── db.py               # Connexion SQL Server
│
├── .env.example            # Template variables d'environnement
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 2. Modules Python

### 2.1 Graphe de dépendances

```
notebooks/
    └── import sys; sys.path.insert(0, '..')
            │
            ├── src/fetch_data.py
            │       └── requests, pandas, os, dotenv
            │
            ├── src/fetch_external.py
            │       └── requests, pandas, io, pathlib, dotenv
            │
            ├── src/clean_data.py
            │       └── pandas, pathlib, os
            │
            ├── src/models.py
            │       └── pandas, numpy, statsmodels, prophet, sklearn
            │
            ├── src/visualize.py
            │       └── pandas, matplotlib, seaborn, plotly
            │
            ├── src/vault.py            ← NE dépend d'aucun autre module src/
            │       └── azure-identity, azure-keyvault-secrets, os, functools
            │
            └── src/db.py
                    ├── src/vault.py    ← récupère le secret SQL
                    └── sqlalchemy, pyodbc, pandas, os, functools
```

### 2.2 `src/fetch_data.py` — Ingestion CNAV

**Responsabilité :** Interroger l'API OpenDataSoft et persister chaque dataset en Parquet.

| Fonction | Signature | Description |
|---|---|---|
| `list_datasets()` | `() → list[dict]` | Liste les 18+ datasets disponibles |
| `fetch_dataset()` | `(dataset_id, limit) → DataFrame` | Télécharge un dataset (défaut : 10 000 lignes) |
| `download_all()` | `(output_dir) → None` | Lance l'ingestion complète |

**Point d'attention :** l'API est paginée mais la plupart des datasets ont < 10 000 lignes. Augmenter `limit` si un dataset est tronqué (vérifier `nb_records` dans le catalogue).

### 2.3 `src/fetch_external.py` — Ingestion sources externes

| Fonction | Source | Mode |
|---|---|---|
| `fetch_insee_serie()` | INSEE API BDM | REST (token optionnel) |
| `fetch_insee_inflation()` | INSEE série 000641194 | Raccourci BDM |
| `fetch_insee_taux_activite_seniors()` | INSEE série 001595978 | Raccourci BDM |
| `fetch_insee_pyramide_from_excel()` | Fichier Excel INSEE | Parsing local |
| `load_cor_projections()` | Fichier Excel/CSV COR | Parsing local |
| `load_drees_pensions()` | Fichier Excel DREES | Parsing local par onglet |

**Note :** INSEE BDM nécessite un token (gratuit, inscription sur api.insee.fr). COR et DREES nécessitent un téléchargement manuel annuel.

### 2.4 `src/clean_data.py` — Nettoyage

**Pipeline de nettoyage appliqué à chaque Parquet brut :**
1. `normalize_columns()` → snake_case, suppression accents, caractères spéciaux
2. `cast_numeric_columns()` → conversion automatique des colonnes numériques
3. `drop_duplicates()` → déduplication
4. Sauvegarde dans `data/processed/`

### 2.5 `src/models.py` — Modèles prédictifs

| Fonction | Méthode | Usage recommandé |
|---|---|---|
| `forecast_arima()` | ARIMA (statsmodels) | Séries courtes, tendances linéaires |
| `forecast_prophet()` | Prophet (Meta) | Séries avec ruptures (réformes), saisonnalité |
| `fit_linear()` | Régression linéaire (sklearn) | Corrélation avec inflation, SMPT |
| `evaluate()` | MAE + RMSE | Comparaison de modèles |

**Choix ARIMA vs Prophet :**
- ARIMA : meilleur sur des séries stationnaires courtes (< 30 points). Paramètre `order=(1,1,1)` par défaut.
- Prophet : robuste aux changements de régime (idéal pour intégrer les dates de réformes comme `changepoints`).

### 2.6 `src/visualize.py` — Visualisations

| Fonction | Bibliothèque | Sortie |
|---|---|---|
| `plot_time_series()` | matplotlib | Figure statique (PNG via `save_fig`) |
| `plot_forecast()` | matplotlib | Série historique + projection |
| `plot_gender_gap()` | plotly | Figure interactive HTML |
| `plot_carsat_map()` | plotly express | Bar chart horizontal trié |

Toutes les figures statiques sont sauvegardées dans `reports/` via `save_fig()`.

### 2.7 `src/vault.py` — Accès Key Vault

```python
from src.vault import get_secret

password = get_secret("SQL-SACredential")   # récupère depuis sifa-vault1
```

Le client `SecretClient` est mis en cache (`@lru_cache`) — un seul appel réseau par session Python.

**Authentification :** `ClientSecretCredential` (azure-identity) — les trois paramètres sont résolus ainsi :

| Paramètre | Source |
|---|---|
| `AZURE_TENANT_ID` | `os.getenv()` depuis `.env` (identifiant public) |
| `AZURE_CLIENT_ID` | `os.getenv()` depuis `.env` (identifiant public) |
| `AZURE_CLIENT_SECRET` | `os.getenv()` → puis `winreg` HKLM → puis `winreg` HKCU |

`AZURE_CLIENT_SECRET` n'est **jamais** dans un fichier. Il est écrit dans le registre Windows lors du setup initial par `scripts/setup_credentials.ps1`, et lu à chaque démarrage directement via `winreg.OpenKey()` — sans passer par les variables d'environnement héritées du shell.

### 2.8 `src/db.py` — Connexion SQL Server

```python
from src.db import read_sql, to_sql

df = read_sql("SELECT * FROM rpt.v_DashboardPrincipal WHERE annee >= 2000")
to_sql(df_processed, table="RetraitesEffectifs", schema="fact")
```

La chaîne de connexion est construite dynamiquement à partir des variables d'env + secret vault :
```
mssql+pyodbc://sa:<vault-secret>@localhost\MSSQLSERVER2022/RetraitesOpenData
    ?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=yes
```

---

## 3. Notebooks

### Séquence d'exécution recommandée

```
fetch_data.py  →  clean_data.py  →  01_exploration  →  02_descriptive_stats
                                                             │
                                         fetch_external.py  ↓
                                                       03_predictive_models
                                                             │
                                                       04_regional_analysis
```

### 3.1 `01_exploration.ipynb`
- Lister les datasets disponibles via l'API
- Inspecter le schéma et la qualité (valeurs manquantes, types)
- Identifier les noms de colonnes réels après téléchargement
- **Output :** mapping `dataset_api_id` → colonnes à mettre à jour dans `clean_data.py`

### 3.2 `02_descriptive_stats.ipynb`
- Évolution des effectifs retraités (H/F, national, par CARSAT)
- Distribution des âges à l'attribution
- Évolution des montants de pension
- Écart H/F (montant, âge, durée)
- **Output :** visualisations PNG dans `reports/`

### 3.3 `03_predictive_models.ipynb`
- Projection ARIMA des effectifs (horizon 10 ans)
- Projection Prophet des montants (avec dates de réformes en changepoints)
- Régression montant vs inflation INSEE
- Comparaison avec projections COR
- **Output :** modèles sauvegardés + visualisations

### 3.4 `04_regional_analysis.ipynb`
- Classement des CARSAT par volume d'attributions
- Clustering K-Means (profil démographique + économique)
- Projection par caisse
- **Output :** carte interactive plotly

---

## 4. Variables d'environnement

Copier `.env.example` en `.env` et adapter :

| Variable | Défaut | Description |
|---|---|---|
| `BASE_URL` | `https://data.assuranceretraite.fr/...` | URL API OpenDataSoft |
| `DATA_RAW_DIR` | `data/raw` | Dossier Parquet bruts |
| `DATA_PROCESSED_DIR` | `data/processed` | Dossier Parquet nettoyés |
| `AZURE_KEYVAULT_URL` | `https://sifa-vault1.vault.azure.net/` | URL Key Vault |
| `AZURE_TENANT_ID` | `90b590b6-5ccc-471c-a0b0-8ee1389e07c7` | Tenant Azure AD (identifiant public) |
| `AZURE_CLIENT_ID` | `2ae721a6-4ae1-45b3-8bb3-dba87845a23f` | App ID du SP `sp-sifa-datasvc` (public) |
| `AZURE_CLIENT_SECRET` | *(absent — dans le registre Windows)* | **NE PAS METTRE dans `.env`** |
| `SQL_SERVER` | `localhost\MSSQLSERVER2022` | Instance SQL Server |
| `SQL_DATABASE` | `RetraitesOpenData` | Nom de la base |
| `SQL_USER` | `sa` | Compte SQL Server |
| `SQL_SECRET_NAME` | `SQL-SACredential` | Nom du secret dans Key Vault |
| `SQL_ODBC_DRIVER` | `ODBC Driver 18 for SQL Server` | Pilote ODBC |
| `JUPYTER_PORT` | `8888` | Port Jupyter |
| `JUPYTER_IP` | `0.0.0.0` | Interface d'écoute Jupyter |
