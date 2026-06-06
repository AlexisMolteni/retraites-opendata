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
    """Récupère une série temporelle INSEE via l'API BDM (format SDMX XML)."""
    import xml.etree.ElementTree as ET
    headers = {"Accept": "application/xml"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{INSEE_BASE}/data/SERIES_BDM/{serie_id}"
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    rows = []
    for elem in root.iter():
        if elem.tag.split("}")[-1] == "Obs":
            period = elem.attrib.get("TIME_PERIOD", "")
            value  = elem.attrib.get("OBS_VALUE")
            rows.append({"periode": period, "valeur": value})
    df = pd.DataFrame(rows)
    df["annee"] = pd.to_numeric(df["periode"].str[:4], errors="coerce")
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
    df["serie_id"] = serie_id
    # Séries mensuelles/trimestrielles → moyenne annuelle
    if df["periode"].str.len().max() > 4:
        df = df.groupby(["annee", "serie_id"], as_index=False)["valeur"].mean()
    return df.dropna(subset=["annee"]).sort_values("annee").reset_index(drop=True)


def fetch_insee_inflation(token: str = "") -> pd.DataFrame:
    """IPC — série 000641194 (indice des prix à la consommation, base 2015)."""
    return fetch_insee_serie("000641194", token)


def fetch_insee_chomage_seniors(token: str = "") -> pd.DataFrame:
    """Taux de chômage BIT 50 ans et plus — série 001688530 (trimestriel → annuel)."""
    return fetch_insee_serie("001688530", token)


def fetch_insee_chomage_ensemble(token: str = "") -> pd.DataFrame:
    """Taux de chômage BIT ensemble — série 001688526 (trimestriel → annuel)."""
    return fetch_insee_serie("001688526", token)


def fetch_insee_mortalite(token: str = "") -> pd.DataFrame:
    """Taux de mortalité pour 1000 habitants — série 001641593 (annuel)."""
    return fetch_insee_serie("001641593", token)


def fetch_insee_natalite(token: str = "") -> pd.DataFrame:
    """Naissances mensuelles → total annuel — série 001641601."""
    return fetch_insee_serie("001641601", token)


def fetch_insee_population(token: str = "") -> pd.DataFrame:
    """Population France (début de mois → moyenne annuelle) — série 001641607."""
    return fetch_insee_serie("001641607", token)


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
    series = {
        "insee_inflation":        ("000641194", "IPC - indice des prix a la consommation"),
        "insee_chomage_seniors":  ("001688530", "Taux chomage BIT 50 ans et plus"),
        "insee_chomage_ensemble": ("001688526", "Taux chomage BIT ensemble"),
        "insee_mortalite":        ("001641593", "Taux de mortalite"),
        "insee_natalite":         ("001641601", "Naissances par mois"),
        "insee_population":       ("001641607", "Population France"),
    }
    for name, (serie_id, label) in series.items():
        print(f"INSEE - {label}...")
        try:
            df = fetch_insee_serie(serie_id, token)
            _save(df, name)
        except Exception as e:
            print(f"  ERREUR : {e}")


if __name__ == "__main__":
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    download_insee_api(token)
    print("\nPour INSEE Pyramide, COR et DREES : télécharger les fichiers Excel")
    print("et appeler load_insee_pyramide_from_excel(), load_cor_projections(), load_drees_pensions()")
