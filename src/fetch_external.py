"""Chargement des sources INSEE externes (espérance de vie, pyramide des âges)."""
import re
from pathlib import Path

import openpyxl
import pandas as pd

RAW_EXT = Path("data/raw/external")
RAW_DIR = Path("data/raw")


def _to_float(val) -> float | None:
    if val is None:
        return None
    s = str(val).replace("nd", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def load_esperance_vie(filepath=None) -> pd.DataFrame:
    """
    Parse fm_dod_mortalite.xlsx (France métropolitaine, 1946-2023).
    Extrait l'espérance de vie à 60 et 65 ans pour H et F.

    Structure de la feuille 'Mortalité' :
      row 0 : titre
      row 2 : groupes ('Hommes' cols 2-7, 'Femmes' cols 8-13)
      row 3 : sous-en-têtes (à 0 an, à 1 an, à 20 ans, à 40 ans, à 60 ans, à 65 ans)
      rows 4-81 : données 1946-2023 (col 0 = année, col 1 = '(p)' si provisoire)
        col 6 : H@60, col 7 : H@65, col 12 : F@60, col 13 : F@65
    """
    if filepath is None:
        filepath = RAW_EXT / "fm_dod_mortalite.xlsx"
    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    records = []
    for row in rows[4:82]:
        annee = row[0]
        if annee is None:
            continue
        try:
            annee = int(annee)
        except (ValueError, TypeError):
            continue
        for genre_code, age_ref, col_idx in [
            ("H", 60, 6),
            ("H", 65, 7),
            ("F", 60, 12),
            ("F", 65, 13),
        ]:
            val = _to_float(row[col_idx]) if col_idx < len(row) else None
            if val is not None:
                records.append({
                    "annee": annee,
                    "genre_code": genre_code,
                    "age_reference": age_ref,
                    "esperance_annees": val,
                    "type_mesure": "conjoncturelle",
                    "source_fichier": "INSEE_fm_dod_mortalite",
                })
    return pd.DataFrame(records)


def load_pyramide_from_csv(filepath=None) -> pd.DataFrame:
    """Parse le CSV INSEE 'donnees_pyramide_proj.csv' (pop par age, sexe, annee)."""
    if filepath is None:
        filepath = RAW_EXT / "donnees_pyramide_proj.csv"
    df = pd.read_csv(filepath, sep=";")
    df.columns = df.columns.str.strip().str.upper()
    needed = {"ANNEE", "AGE", "POP"}
    if not needed.issubset(set(df.columns)):
        # Essayer sep=","
        df = pd.read_csv(filepath, sep=",")
        df.columns = df.columns.str.strip().str.upper()
    df = df.rename(columns={"ANNEE": "annee", "AGE": "age", "POP": "population"})
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
    df["age"]   = pd.to_numeric(df["age"],   errors="coerce").astype("Int64")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").astype("Int64")
    if "SEXE" in df.columns:
        df["genre_code"] = df["SEXE"].map({"M": "H", "H": "H", "F": "F", 1: "H", 2: "F"})
    elif "genre_code" not in df.columns:
        raise ValueError("Colonne SEXE / genre_code introuvable")
    df = df[["annee", "age", "genre_code", "population"]].dropna()
    df["source_fichier"] = df["annee"].apply(lambda a: "INSEE_PROJ" if a >= 2024 else "INSEE_OBS")
    return df.drop_duplicates(subset=["annee", "age", "genre_code"])
