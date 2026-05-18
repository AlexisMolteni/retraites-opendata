"""
Ingestion des sources externes : INSEE, COR, DREES.
Chaque fonction retourne un DataFrame prêt pour l'import SQL.
"""
import requests
import pandas as pd
import io
import os
from pathlib import Path

RAW_DIR = Path(os.getenv("DATA_RAW_DIR", "data/raw")) / "external"

INSEE_BASE = "https://api.insee.fr/series/BDM/V1"


def _save(df: pd.DataFrame, name: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"  → {len(df)} lignes  →  {path}")
    return path


# ── INSEE — Séries BDM via API ────────────────────────────────────────────────
# Nécessite token INSEE (gratuit) : https://api.insee.fr/catalogue/
# Sans token : téléchargement manuel des fichiers Excel

def fetch_insee_serie(serie_id: str, token: str = "") -> pd.DataFrame:
    """Récupère une série temporelle INSEE via l'API BDM."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{INSEE_BASE}/data/SERIES_BDM/{serie_id}"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    obs = r.json()["seriesData"][0]["Obs"]
    df = pd.DataFrame(obs)[["time-period", "obs-value"]].rename(
        columns={"time-period": "annee", "obs-value": "valeur"}
    )
    df["serie_id"] = serie_id
    df["annee"] = pd.to_numeric(df["annee"].str[:4], errors="coerce")
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
    return df.dropna(subset=["annee"])


def fetch_insee_inflation(token: str = "") -> pd.DataFrame:
    """IPC — série 000641194 (indice des prix à la consommation)."""
    return fetch_insee_serie("000641194", token)


def fetch_insee_taux_activite_seniors(token: str = "") -> pd.DataFrame:
    """Taux d'activité 55-64 ans — série 001595978."""
    return fetch_insee_serie("001595978", token)


# ── INSEE — Pyramide des âges (fichier Excel public) ─────────────────────────

def fetch_insee_pyramide_from_excel(filepath: str) -> pd.DataFrame:
    """
    Parse le fichier Excel INSEE 'pop-totale-france.xlsx'.
    Télécharger depuis : https://www.insee.fr/fr/statistiques/1893198
    """
    df = pd.read_excel(filepath, sheet_name=0, skiprows=4)
    # Structure attendue : colonne Âge + colonnes par année
    # À adapter selon le format réel du fichier
    df = df.rename(columns={df.columns[0]: "age"})
    df = df.melt(id_vars="age", var_name="annee", value_name="population")
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    return df.dropna()


# ── COR — Projections (CSV/Excel téléchargés manuellement) ───────────────────

def load_cor_projections(filepath: str) -> pd.DataFrame:
    """
    Parse un fichier de projections COR (format CSV ou Excel).
    Structure cible : scenario, annee, indicateur, valeur
    Télécharger depuis : https://www.cor-retraites.fr/simulateur/projections
    """
    ext = Path(filepath).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(filepath, sep=";", decimal=",")
    else:
        df = pd.read_excel(filepath)

    # Normalisation minimaliste — adapter selon le fichier réel
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    _save(df, "cor_projections")
    return df


# ── DREES — Retraités et retraites (Excel annuel) ────────────────────────────

def load_drees_pensions(filepath: str, sheet: str = "pension_moyenne") -> pd.DataFrame:
    """
    Parse un onglet du fichier DREES 'Les retraités et les retraites'.
    Télécharger depuis :
    https://drees.solidarites-sante.gouv.fr/publications/panoramas-de-la-drees/les-retraites-et-les-retraites
    """
    df = pd.read_excel(filepath, sheet_name=sheet, skiprows=2)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    _save(df, f"drees_{sheet}")
    return df


# ── Point d'entrée ────────────────────────────────────────────────────────────

def download_insee_api(token: str = "") -> None:
    print("INSEE — inflation...")
    try:
        df = fetch_insee_inflation(token)
        _save(df, "insee_inflation")
    except Exception as e:
        print(f"  ✗ {e} (token requis ou téléchargement manuel)")

    print("INSEE — taux activité seniors...")
    try:
        df = fetch_insee_taux_activite_seniors(token)
        _save(df, "insee_taux_activite_seniors")
    except Exception as e:
        print(f"  ✗ {e}")


if __name__ == "__main__":
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    download_insee_api(token)
    print("\nPour INSEE Pyramide, COR et DREES : télécharger les fichiers Excel")
    print("et appeler load_insee_pyramide_from_excel(), load_cor_projections(), load_drees_pensions()")
