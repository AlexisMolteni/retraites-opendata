# Projet : Statistiques & Prédictif — Données Ouvertes Assurance Retraite

## Contexte

Exploitation des données ouvertes du portail **data.assuranceretraite.fr** (régime général CNAV/CARSAT).  
Source : API OpenDataSoft publique, licence Etalab Open License v2.0.  
Objectif : produire des statistiques descriptives et des modèles prédictifs sur le système de retraite français.

---

## Datasets disponibles (19 au total)

| ID dataset (à confirmer via API) | Thème | Série depuis | Enregistrements |
|---|---|---|---|
| Âge moyen au 31/12 | Âges | 1974 | 52 |
| Âge moyen à l'attribution | Âges | — | 63 |
| Distribution des âges à l'attribution (tous droits) | Assurés & Retraités | — | 2 518 |
| Distribution des âges — droits dérivés | Assurés & Retraités | 1963 | 2 499 |
| Attributions annuelles par CARSAT | Assurés & Retraités | — | 1 119 |
| Attributions annuelles par type de droit | Assurés & Retraités | — | 126 |
| Retraités par CARSAT au 31/12 | Assurés & Retraités | 1960 | 66 |
| Retraités par genre au 31/12 | Assurés & Retraités | 1974 | 104 |
| Retraités par type de cotisation au 31/12 | Assurés & Retraités | — | 66 |
| Durée d'assurance (limitée/illimitée) | Assurés & Retraités | — | 118 |
| Montant de base par catégorie de pension | Droits Retraités | — | 756 |
| Montant de base — droits directs | Droits Retraités | — | 189 |
| Montant global par genre | Droits Retraités | — | 123 |
| Montant global par type de droit au 31/12 | Droits Retraités | — | 116 |
| Montant global par type de droit et genre | Droits Retraités | — | 378 |
| Montant global au 31/12 | Droits Retraités | 1960 | 66 |
| Montant global — bénéficiaires minimum vieillesse | Droits Retraités | — | 96 |
| Revenu annuel moyen des pensions attribuées | Droits Retraités | — | 187 |

**API base URL :** `https://data.assuranceretraite.fr/api/explore/v2.1/catalog/datasets`

---

## Structure du projet à créer sur le serveur

```
retraites-opendata/
├── data/
│   ├── raw/          # données brutes téléchargées via API
│   └── processed/    # données nettoyées et enrichies
├── notebooks/
│   ├── 01_exploration.ipynb       # discovery, qualité des données
│   ├── 02_descriptive_stats.ipynb # statistiques et visualisations
│   ├── 03_predictive_models.ipynb # modèles prédictifs
│   └── 04_regional_analysis.ipynb # analyse par CARSAT
├── src/
│   ├── fetch_data.py     # ingestion via API OpenDataSoft
│   ├── clean_data.py     # nettoyage et normalisation
│   ├── models.py         # modèles ARIMA / Prophet
│   └── visualize.py      # fonctions de visualisation réutilisables
├── reports/              # exports HTML/PDF des analyses
├── requirements.txt
├── .env.example          # variables d'environnement (pas de secret ici, API publique)
└── README.md
```

---

## Dépendances Python (requirements.txt)

```
pandas>=2.0
numpy>=1.25
requests>=2.31
python-dotenv>=1.0
matplotlib>=3.7
seaborn>=0.13
plotly>=5.18
jupyter>=1.0
notebook>=7.0
ipykernel>=6.0
statsmodels>=0.14
prophet>=1.1
scikit-learn>=1.3
openpyxl>=3.1
```

---

## Installation sur le serveur

### Prérequis
- Python 3.10+ installé
- pip ou conda disponible
- Accès internet sortant vers `data.assuranceretraite.fr`

### Linux (Ubuntu/Debian)

```bash
# 1. Cloner / créer le dossier projet
mkdir -p /opt/projets/retraites-opendata && cd /opt/projets/retraites-opendata

# 2. Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Lancer Jupyter (accessible en réseau)
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --NotebookApp.token='choisir_un_token'
```

### Windows Server

```powershell
# 1. Créer le dossier projet
New-Item -ItemType Directory -Path "C:\Projets\retraites-opendata" -Force
Set-Location "C:\Projets\retraites-opendata"

# 2. Créer l'environnement virtuel
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Lancer Jupyter
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

---

## Accès à Jupyter depuis ta machine locale

Une fois Jupyter lancé sur le serveur, ouvrir dans un navigateur :

```
http://WWDBA01-D01.groupesifa.com:8888
```

> **Note sécurité :** penser à définir un token fort ou un mot de passe via `jupyter notebook password`, et à ouvrir le port 8888 uniquement sur le réseau interne.

---

## Ingestion des données — exemple de script de démarrage

```python
# src/fetch_data.py
import requests
import pandas as pd
import os

BASE_URL = "https://data.assuranceretraite.fr/api/explore/v2.1/catalog/datasets"

def list_datasets():
    r = requests.get(f"{BASE_URL}?limit=50&lang=fr")
    r.raise_for_status()
    return r.json()["results"]

def fetch_dataset(dataset_id: str, limit: int = 10000) -> pd.DataFrame:
    url = f"{BASE_URL}/{dataset_id}/records?limit={limit}&lang=fr"
    r = requests.get(url)
    r.raise_for_status()
    records = r.json()["results"]
    return pd.DataFrame(records)

def download_all(output_dir: str = "data/raw"):
    os.makedirs(output_dir, exist_ok=True)
    for ds in list_datasets():
        ds_id = ds["dataset_id"]
        print(f"Téléchargement : {ds_id}")
        df = fetch_dataset(ds_id)
        df.to_parquet(f"{output_dir}/{ds_id}.parquet", index=False)
        print(f"  → {len(df)} enregistrements sauvegardés")

if __name__ == "__main__":
    download_all()
```

---

## Axes prédictifs prioritaires

| Modèle | Variable cible | Méthode suggérée | Horizon |
|---|---|---|---|
| Évolution des effectifs | Nombre de retraités au 31/12 | ARIMA / Prophet | 5-10 ans |
| Montant moyen de pension | Pension base droits directs | Régression + inflation | 3-5 ans |
| Âge moyen d'attribution | Âge départ direct | Détection rupture (réformes) + trend | 5 ans |
| Gap H/F montants | Écart montant H vs F | Modèle de convergence | 10 ans |
| Pression régionale | Attributions par CARSAT | Clustering + projection | 5 ans |

---

## Enrichissements de données recommandés

- **INSEE** — pyramide des âges, espérance de vie : `https://www.insee.fr/fr/statistiques`
- **COR** — projections officielles système de retraite : `https://www.cor-retraites.fr`
- **DREES** — données multi-régimes (AGIRC-ARRCO) : `https://drees.solidarites-sante.gouv.fr`

---

## Prochaines étapes

- [ ] Déposer ce fichier sur le serveur et créer la structure de dossiers
- [ ] Lancer `python src/fetch_data.py` pour télécharger tous les datasets
- [ ] Ouvrir `notebooks/01_exploration.ipynb` pour démarrer l'analyse
- [ ] Configurer l'accès Jupyter depuis le réseau local
