"""
Inspection des fichiers Excel DREES pour écrire les parsers.
"""
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd
from pathlib import Path

DL = Path(r"C:\Users\!amolteni\Downloads")

FILES = {
    "vue_ensemble": DL / "Vue%20d%27ensemble.xlsx",
    "fiche01":      DL / "Fiche%2001%20-%20Les%20effectifs%20de%20retrait%C3%A9s.xlsx",
    "fiche10":      DL / "Fiche%2010%20-%20Les%20masses%20financi%C3%A8res%20relatives%20aux%20pensions%20de%20retraite.xlsx",
}


def list_sheets(filepath):
    xl = pd.ExcelFile(filepath)
    print(f"\n{Path(filepath).name}:")
    for s in xl.sheet_names:
        print(f"  -> '{s}'")


def inspect(filepath, sheetname, nrows=30, ncols=22):
    df = pd.read_excel(filepath, sheet_name=sheetname, header=None, nrows=nrows)
    df = df.iloc[:, :ncols]
    print(f"\n{'='*70}")
    print(f"  {Path(filepath).name}  >>  {sheetname}")
    print(f"  Shape: {df.shape}")
    print(f"{'='*70}")
    pd.set_option('display.max_columns', ncols)
    pd.set_option('display.width', 220)
    pd.set_option('display.max_colwidth', 45)
    print(df.to_string())


for f in FILES.values():
    list_sheets(f)

# Graphique 1 — Âge conjoncturel H/F 2004-2023 (déjà vu, structure connue)
# inspect(FILES["vue_ensemble"], "Vue d'ensemble_Graphique 1", nrows=10, ncols=25)

# Fiche 01 : onglets à identifier
for name in ["F01_Tableau 2", "F01_Graphique 2", "F01_Tableau 1"]:
    try:
        inspect(FILES["fiche01"], name, nrows=28, ncols=15)
    except Exception as e:
        print(f"  ERREUR '{name}': {e}")

# Fiche 10
for name in ["F10_Graphique1", "F10_Tableau 1"]:
    try:
        inspect(FILES["fiche10"], name, nrows=35, ncols=42)
    except Exception as e:
        print(f"  ERREUR '{name}': {e}")
