# Retraites OpenData — Statistiques & Prédictif

Exploitation des données ouvertes du portail **data.assuranceretraite.fr** (régime général CNAV/CARSAT) croisées avec les sources INSEE, COR et DREES.

> **Serveur :** `WWDBA01-D01.groupesifa.com` — SQL Server 2022 (`MSSQLSERVER2022`) — Python 3.10

---

## Démarrage rapide

```powershell
# 1. Activer Python
cd d:\DEV\retraites-opendata
.\.venv\Scripts\Activate.ps1

# 2. Authentifier Azure (si token expiré)
Connect-AzAccount -TenantId "90b590b6-5ccc-471c-a0b0-8ee1389e07c7" -UseDeviceAuthentication

# 3. Lancer Jupyter
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

Jupyter : `http://WWDBA01-D01.groupesifa.com:8888`

---

## Documentation

| Document | Description |
|---|---|
| [01 — Vue d'ensemble](docs/01_architecture_overview.md) | Contexte, objectifs, principes d'architecture, choix technologiques |
| [02 — Architecture des données](docs/02_data_architecture.md) | Sources, flux, modèle relationnel SQL, conventions |
| [03 — Architecture applicative](docs/03_application_architecture.md) | Modules Python, notebooks, variables d'environnement |
| [04 — Infrastructure](docs/04_infrastructure.md) | SQL Server, Azure Key Vault, réseau, packages |
| [05 — Sécurité](docs/05_security.md) | Key Vault, Service Principal, comptes SQL, checklist prod |
| [06 — Installation](docs/06_installation.md) | Guide pas à pas pour remettre le projet de zéro |
| [07 — Opérations](docs/07_operations.md) | Démarrage, refresh données, SQL, Jupyter, troubleshooting |
| [08 — Dictionnaire des données](docs/08_data_dictionary.md) | Toutes les tables, colonnes, valeurs codifiées, glossaire |

---

## Structure du projet

```
retraites-opendata/
├── data/raw/           Parquet bruts — 1 fichier par dataset
├── data/processed/     Parquet nettoyés (régénérables)
├── docs/               Documentation architecture (8 fichiers)
├── notebooks/          4 notebooks Jupyter (exploration → modèles → régional)
├── reports/            Exports PNG / HTML / PDF
├── sql/                DDL SQL Server + script Service Principal
├── src/                Modules Python (ingestion, nettoyage, modèles, vault, SQL)
├── .env.example        Template variables d'environnement
├── requirements.txt    Dépendances Python
└── README.md           Ce fichier
```

---

## Sources de données

| Source | Données | Accès |
|---|---|---|
| **CNAV** — data.assuranceretraite.fr | 18 datasets retraite (effectifs, montants, âges, CARSAT) | API REST publique |
| **INSEE** | Pyramide des âges, espérance de vie, inflation | API BDM + Excel |
| **COR** | Projections 2070, scénarios, réformes 1993→2023 | Excel annuel |
| **DREES** | Pensions multi-régimes (AGIRC-ARRCO, MSA, SSI…) | Excel annuel |

---

## Pipeline de données

```
API CNAV / INSEE / COR / DREES
        │
        ▼
src/fetch_data.py + src/fetch_external.py   → data/raw/*.parquet
        │
        ▼
src/clean_data.py                           → data/processed/*.parquet
        │
        ▼
src/db.py → SQL Server RetraitesOpenData    → dim.* / fact.* / ext.*
        │
        ▼
Notebooks Jupyter                           → rpt.* (vues croisées)
        │
        ▼
reports/                                    (PNG, HTML, PDF)
```

---

## Modèles prédictifs

| Modèle | Variable cible | Méthode | Horizon |
|---|---|---|---|
| Effectifs retraités | Nombre au 31/12 | ARIMA / Prophet | 5-10 ans |
| Montant moyen de pension | Pension base droits directs | Régression + inflation | 3-5 ans |
| Âge moyen d'attribution | Âge de départ direct | Prophet + ruptures réformes | 5 ans |
| Gap H/F montants | Écart H vs F | Modèle de convergence | 10 ans |
| Pression régionale | Attributions par CARSAT | Clustering + projection | 5 ans |

---

## Commandes utiles

```powershell
# Télécharger toutes les données CNAV
python src/fetch_data.py

# Nettoyer les données
python src/clean_data.py

# Recréer la base SQL depuis zéro
$pwd = Get-AzKeyVaultSecret -VaultName sifa-vault1 -Name SQL-SACredential -AsPlainText
sqlcmd -S localhost\MSSQLSERVER2022 -U sa -P $pwd -i sql\create_database.sql -b
sqlcmd -S localhost\MSSQLSERVER2022 -U sa -P $pwd -i sql\create_enrichissements.sql -b

# Créer le Service Principal (admin AD, depuis réseau interne)
.\sql\create_service_principal.ps1
```
