# Statistiques & Prédictif — Données Ouvertes Assurance Retraite

Exploitation des données ouvertes du portail **data.assuranceretraite.fr** (régime général CNAV/CARSAT).  
Source : API OpenDataSoft publique, licence Etalab Open License v2.0.

## Installation

```powershell
cd retraites-opendata
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Démarrage rapide

```powershell
# 1. Télécharger tous les datasets
python src/fetch_data.py

# 2. Nettoyer les données
python src/clean_data.py

# 3. Lancer Jupyter
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

Ouvrir ensuite : `http://WWDBA01-D01.groupesifa.com:8888`

## Structure

```
data/raw/          Données brutes (parquet)
data/processed/    Données nettoyées
notebooks/         Analyses Jupyter
src/               Modules Python
reports/           Exports HTML/PNG
```

## Notebooks

| Notebook | Contenu |
|---|---|
| 01_exploration.ipynb | Discovery, qualité des données |
| 02_descriptive_stats.ipynb | Statistiques et visualisations |
| 03_predictive_models.ipynb | ARIMA / Prophet / régression |
| 04_regional_analysis.ipynb | Analyse par CARSAT |

## Axes prédictifs

- Évolution du nombre de retraités (ARIMA / Prophet, horizon 5-10 ans)
- Montant moyen de pension (régression + inflation, 3-5 ans)
- Âge moyen d'attribution (détection ruptures + trend, 5 ans)
- Écart H/F montants (modèle de convergence, 10 ans)
- Pression régionale par CARSAT (clustering + projection, 5 ans)

## Base de données SQL Server

```powershell
# 1. Créer la base (schémas, dimensions, tables de faits, vues)
sqlcmd -S localhost -E -i sql\create_database.sql

# 2. Ajouter les enrichissements externes (INSEE, COR, DREES)
sqlcmd -S localhost -E -i sql\create_enrichissements.sql
```

## Sources complémentaires & croisements

| Source | Données | Ingestion |
|---|---|---|
| **INSEE** | Pyramide des âges, espérance de vie, inflation, taux d'activité | API BDM (token gratuit) + Excel |
| **COR** | Projections 2070, scénarios, réformes 1993→2023 | Excel manuel |
| **DREES** | Pensions multi-régimes (AGIRC-ARRCO, MSA, SSI…) | Excel annuel |

```powershell
# Ingestion sources externes (INSEE API — token optionnel)
python src/fetch_external.py [TOKEN_INSEE]
```

**Vues de croisement disponibles (`rpt` schema) :**
- `v_PensionVsInflation` — pouvoir d'achat réel des pensions
- `v_TauxRetraiteVsPopulation` — taux de retraite vs pyramide des âges
- `v_AgeMoyenVsReformes` — détection de ruptures liées aux réformes
- `v_CompaisonRegimes` — part CNAV dans la pension totale tous régimes
- `v_DureeRetraiteEstimee` — durée de retraite estimée via espérance de vie
- `v_ProjectionVsCOR` — réel CNAV vs 4 scénarios COR (2000-2070)
- `v_DashboardPrincipal` — tableau de bord synthèse multi-sources
