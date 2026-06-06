"""
Ingestion DREES — Panorama "Les retraités et les retraites" (édition 2025).
Fichiers sources : data/raw/external/drees_*.xlsx
"""
import re
import sys
import requests
import pandas as pd
import numpy as np
from pathlib import Path

RAW_EXT = Path("data/raw/external")

# URLs de téléchargement direct (édition 2025, juillet 2025)
DREES_URLS = {
    "drees_vue_ensemble":      "https://drees.solidarites-sante.gouv.fr/sites/default/files/2025-07/Vue%20d%27ensemble.xlsx",
    "drees_fiche01_effectifs": "https://drees.solidarites-sante.gouv.fr/sites/default/files/2025-07/Fiche%2001%20-%20Les%20effectifs%20de%20retrait%C3%A9s.xlsx",
    "drees_fiche10_masses":    "https://drees.solidarites-sante.gouv.fr/sites/default/files/2025-07/Fiche%2010%20-%20Les%20masses%20financi%C3%A8res%20relatives%20aux%20pensions%20de%20retraite.xlsx",
}


def download_drees_files() -> None:
    """Télécharge les fichiers DREES si absents."""
    RAW_EXT.mkdir(parents=True, exist_ok=True)
    for name, url in DREES_URLS.items():
        dest = RAW_EXT / f"{name}.xlsx"
        if dest.exists():
            print(f"  → {dest.name} déjà présent ({dest.stat().st_size:,} octets)")
            continue
        print(f"  Téléchargement {url} …")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"  → {dest.name} ({dest.stat().st_size:,} octets)")


def _clean_year(val) -> int | None:
    """Extrait l'année de valeurs comme '2004', '20181', '2023(p)'."""
    s = re.sub(r"[^0-9]", "", str(val).split(".")[0])[:4]
    return int(s) if len(s) == 4 else None


def _melt_years(label_col: pd.Series, year_row: pd.Series, data_rows: list[tuple]) -> pd.DataFrame:
    """
    Transforme une matrice (lignes=libellés, colonnes=années) en DataFrame long.
    data_rows : liste de (genre_code, values_series)
    """
    years = [_clean_year(v) for v in year_row]
    records = []
    for genre_code, values in data_rows:
        for yr, val in zip(years, values):
            if yr is None:
                continue
            try:
                v = float(str(val).replace("nd", "").strip())
            except ValueError:
                continue
            records.append({"annee": yr, "genre_code": genre_code, "valeur": v})
    return pd.DataFrame(records).dropna()


# ── 1. Âge conjoncturel moyen de départ (Vue d'ensemble_Graphique 1) ─────────

def parse_age_depart() -> pd.DataFrame:
    """
    Âge conjoncturel moyen de départ à la retraite par sexe, 2004-2023.
    → indicateur = 'AGE_CONJONCTUREL_DEPART'
    """
    f = RAW_EXT / "drees_vue_ensemble.xlsx"
    raw = pd.read_excel(f, sheet_name="Vue d'ensemble_Graphique 1", header=None, nrows=10)
    year_row  = raw.iloc[3, 2:]    # 2004 … 2023
    femmes    = raw.iloc[4, 2:]
    hommes    = raw.iloc[5, 2:]
    ensemble  = raw.iloc[6, 2:]

    df = _melt_years(None, year_row, [("F", femmes), ("H", hommes), ("T", ensemble)])
    df["indicateur"]    = "AGE_CONJONCTUREL_DEPART"
    df["regime_id"]     = 99
    df["unite"]         = "annees"
    df["source_fichier"] = "DREES_PANORAMA_2025"
    print(f"  parse_age_depart     : {len(df)} lignes (2004-2023, H/F/T)")
    return df


# ── 2. Effectifs retraités tous régimes (F01_Tableau 1) ──────────────────────

def parse_effectifs_tous_regimes() -> pd.DataFrame:
    """
    Effectifs de retraités droit direct tous régimes (H/F/T), 2004-2023.
    → indicateur = 'NB_RETRAITES_TOUS_REGIMES' (en milliers)
    """
    f = RAW_EXT / "drees_fiche01_effectifs.xlsx"
    raw = pd.read_excel(f, sheet_name="F01_Tableau 1", header=None, nrows=27)
    # Col 1 = annee, col 2 = Femmes, col 3 = Hommes, col 4 = Ensemble
    data = raw.iloc[5:25, [1, 2, 3, 4]].copy()
    data.columns = ["annee", "F", "H", "T"]
    data["annee"] = data["annee"].apply(_clean_year)
    data = data.dropna(subset=["annee"])
    data["annee"] = data["annee"].astype(int)

    rows = []
    for _, r in data.iterrows():
        for gc in ("F", "H", "T"):
            try:
                v = float(r[gc])
            except (ValueError, TypeError):
                continue
            rows.append({"annee": r["annee"], "genre_code": gc, "valeur": v})

    df = pd.DataFrame(rows)
    df["indicateur"]    = "NB_RETRAITES_TOUS_REGIMES"
    df["regime_id"]     = 99
    df["unite"]         = "milliers"
    df["source_fichier"] = "DREES_PANORAMA_2025"
    print(f"  parse_effectifs      : {len(df)} lignes (2004-2023, H/F/T)")
    return df


# ── 3. Nouveaux retraités (F01_Graphique 2) ──────────────────────────────────

def parse_nouveaux_retraites() -> pd.DataFrame:
    """
    Flux annuels de nouveaux retraités de droit direct, 2005-2023.
    → indicateurs = 'NOUVEAUX_RETRAITES', 'VARIATION_NB_RETRAITES', 'EVOL_NB_RETRAITES_PCT'
    """
    f = RAW_EXT / "drees_fiche01_effectifs.xlsx"
    raw = pd.read_excel(f, sheet_name="F01_Graphique 2", header=None, nrows=23)
    # Col 1 = annee, col 2 = nouveaux (milliers), col 3 = variation (milliers), col 4 = évol %
    data = raw.iloc[3:22, [1, 2, 3, 4]].copy()
    data.columns = ["annee", "nouveaux", "variation", "evol_pct"]
    data["annee"] = data["annee"].apply(_clean_year)
    data = data.dropna(subset=["annee"])
    data["annee"] = data["annee"].astype(int)

    rows = []
    for _, r in data.iterrows():
        for col, indic, unite in [
            ("nouveaux",   "NOUVEAUX_RETRAITES",       "milliers"),
            ("variation",  "VARIATION_NB_RETRAITES",   "milliers"),
            ("evol_pct",   "EVOL_NB_RETRAITES_PCT",    "%"),
        ]:
            try:
                v = float(str(r[col]).replace("nd", "").strip())
            except (ValueError, TypeError):
                continue
            rows.append({"annee": r["annee"], "genre_code": "T",
                         "indicateur": indic, "valeur": v, "unite": unite})

    df = pd.DataFrame(rows)
    df["regime_id"]      = 99
    df["source_fichier"] = "DREES_PANORAMA_2025"
    print(f"  parse_nouveaux       : {len(df)} lignes (2005-2023)")
    return df


# ── 4. Masses financières et part PIB (F10_Graphique1) ───────────────────────

def parse_masses_financieres() -> pd.DataFrame:
    """
    Masses financières relatives aux pensions de retraite, 1990-2023.
    → indicateurs = 'PRESTATIONS_DD_MDS_EUR', 'PRESTATIONS_DDE_MDS_EUR',
                    'PRESTATIONS_TOTAL_MDS_EUR', 'PART_DD_PIB_PCT', 'PART_DDE_PIB_PCT',
                    'PART_TOTAL_PIB_PCT'
    """
    f = RAW_EXT / "drees_fiche10_masses.xlsx"
    raw = pd.read_excel(f, sheet_name="F10_Graphique1", header=None, nrows=19)

    year_row  = raw.iloc[3,  2:].tolist()
    dd_mio    = raw.iloc[5,  2:]   # Droit direct (millions €)
    dde_mio   = raw.iloc[6,  2:]   # Droit dérivé (millions €)
    tot_mio   = raw.iloc[4,  2:]   # Total vieillesse-survie
    dd_pib    = raw.iloc[15, 2:]   # Droit direct % PIB
    dde_pib   = raw.iloc[16, 2:]   # Droit dérivé % PIB
    tot_pib   = raw.iloc[14, 2:]   # Total % PIB

    rows = []
    for i, yr_raw in enumerate(year_row):
        yr = _clean_year(yr_raw)
        if yr is None:
            continue
        for series, indic, unite, scale in [
            (dd_mio,  "PRESTATIONS_DD_MDS_EUR",    "milliards_eur", 1e-3),
            (dde_mio, "PRESTATIONS_DDE_MDS_EUR",   "milliards_eur", 1e-3),
            (tot_mio, "PRESTATIONS_TOTAL_MDS_EUR", "milliards_eur", 1e-3),
            (dd_pib,  "PART_DD_PIB_PCT",           "%",             1.0),
            (dde_pib, "PART_DDE_PIB_PCT",          "%",             1.0),
            (tot_pib, "PART_TOTAL_PIB_PCT",        "%",             1.0),
        ]:
            try:
                v = round(float(series.iloc[i]) * scale, 4)
            except (ValueError, TypeError, IndexError):
                continue
            rows.append({"annee": yr, "genre_code": "T",
                         "indicateur": indic, "valeur": v, "unite": unite})

    df = pd.DataFrame(rows)
    df["regime_id"]      = 99
    df["source_fichier"] = "DREES_PANORAMA_2025"
    print(f"  parse_masses         : {len(df)} lignes (1990-2023)")
    return df


# ── Point d'entrée ────────────────────────────────────────────────────────────

def fetch_all_drees(download: bool = False) -> pd.DataFrame:
    """
    Agrège les 4 parsers en un seul DataFrame et sauvegarde en Parquet.
    download=True : télécharge les fichiers si absents.
    """
    if download:
        download_drees_files()

    parts = [
        parse_age_depart(),
        parse_effectifs_tous_regimes(),
        parse_nouveaux_retraites(),
        parse_masses_financieres(),
    ]
    df = pd.concat(parts, ignore_index=True)
    df["annee"]   = df["annee"].astype(int)
    df["valeur"]  = pd.to_numeric(df["valeur"], errors="coerce")
    df = df.dropna(subset=["valeur"])

    out = RAW_EXT / "drees_panorama_2025.parquet"
    df.to_parquet(out, index=False)
    print(f"\n  → {len(df)} lignes  →  {out}")
    return df


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from dotenv import load_dotenv
    load_dotenv()
    df = fetch_all_drees(download=True)
    print(df.groupby("indicateur")[["annee", "valeur"]].agg(
        {"annee": ["min", "max"], "valeur": "count"}
    ))
