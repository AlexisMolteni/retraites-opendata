"""
Chargement des fichiers Parquet vers SQL Server (tables fact.* et ext.*).
Lance : python -m src.load_sql
"""
from dotenv import load_dotenv
load_dotenv()

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
from pathlib import Path
from src.db import engine, to_sql
from src.fetch_external import load_pyramide_from_csv
from src.fetch_drees import fetch_all_drees
import sqlalchemy as sa

PRO = Path("data/processed")

# ── Référentiels ─────────────────────────────────────────────────────────────

GENRE_MAP = {
    "Hommes": 1, "hommes": 1, "H": 1, "M": 1,
    "Femmes": 2, "femmes": 2, "F": 2,
    "Total":  3, "total":  3, "T": 3,
    "Ensemble": 3,
}

TYPE_DROIT_MAP = {
    "droits_directs":  1,
    "droits_derives":  2,
    "droits_derives_1": 2,
    "droits_mixtes":   3,
    "total":           4,
}

# Mapping dataset city → carsat_id (dim.CARSAT)
CARSAT_MAP = {
    "Bordeaux":         2,
    "Clermont Ferrand": 3,
    "Dijon":            5,
    "Guadeloupe":       17,
    "Guyane":           17,
    "La R\xe9union":    17,   # La Réunion (encodage)
    "La Reunion":       17,
    "Lille":            12,
    "Limoges":          10,
    "Lyon":             15,
    "Marseille":        18,   # CARSAT Sud-Est
    "Martinique":       17,
    "Montpellier":      9,
    "Nancy":            13,
    "Nantes":           14,
    "Orl\xe9ans":       7,    # Orléans
    "Orleans":          7,
    "Paris":            16,
    "Rennes":           6,
    "Rouen":            8,
    "Strasbourg":       1,
    "Toulouse":         11,
}


def _truncate(table: str, schema: str = "fact") -> None:
    """Vide une table avant rechargement."""
    with engine().begin() as conn:
        conn.execute(sa.text(f"DELETE FROM [{schema}].[{table}]"))


def _ensure_carsat_sudest() -> None:
    """Ajoute CARSAT Sud-Est (id=18) si absent."""
    with engine().begin() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM dim.CARSAT WHERE carsat_id = 18")
        ).fetchone()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO dim.CARSAT (carsat_id, code, libelle, region) "
                "VALUES (18, 'CARSAT-SE', N'CARSAT Sud-Est', N'PACA')"
            ))
            print("  → dim.CARSAT : ajout CARSAT Sud-Est (id=18)")


# ── 1. fact.RetraitesEffectifs ────────────────────────────────────────────────

def load_effectifs() -> int:
    df = pd.read_parquet(PRO / "nombre-de-retraites-au-31-decembre-par-genre.parquet")
    df = df.dropna(subset=["annees_transfo", "sexe", "nombre_de_retraites"])
    df["annee_id"]           = df["annees_transfo"].astype(int)
    df["genre_id"]           = df["sexe"].map(GENRE_MAP)
    df["carsat_id"]          = 99          # France entière
    df["type_cotisation_id"] = 9           # Total
    df["nb_retraites"]       = df["nombre_de_retraites"].astype(int)

    out = df[["annee_id", "genre_id", "carsat_id", "type_cotisation_id", "nb_retraites"]].dropna()
    _truncate("RetraitesEffectifs")
    n = to_sql(out, "RetraitesEffectifs")
    return len(out)


# ── 2. fact.Attributions ─────────────────────────────────────────────────────

def load_attributions() -> int:
    df = pd.read_parquet(PRO / "attribution-de-lannee-par-region-debitrice.parquet")
    df = df.dropna(subset=["annees", "carsat", "effectif"])
    df["annee_id"]      = df["annees"].astype(int)
    df["carsat_id"]     = df["carsat"].map(CARSAT_MAP)
    df["type_droit_id"] = 1   # Droits directs (dataset ne ventile pas)
    df["genre_id"]      = 3   # Total
    df["nb_attributions"] = df["effectif"].astype(int)

    out = (df[["annee_id", "carsat_id", "type_droit_id", "genre_id", "nb_attributions"]]
           .dropna()
           .groupby(["annee_id", "carsat_id", "type_droit_id", "genre_id"], as_index=False)
           ["nb_attributions"].sum())   # agrège les 4 DOM → carsat_id=17

    _truncate("Attributions")
    n = to_sql(out, "Attributions")
    return len(out)


# ── 3. fact.Ages ─────────────────────────────────────────────────────────────

def load_ages() -> int:
    df = pd.read_parquet(PRO / "age-moyen-a-lattribution.parquet")
    df = df.dropna(subset=["annee"])

    rows = []
    col_droit = {
        "droits_directs":   1,
        "droits_derives_1": 2,
        "total":            4,
    }
    for col, td_id in col_droit.items():
        sub = df[["annee", col]].dropna()
        rows.append(pd.DataFrame({
            "annee_id":       sub["annee"].astype(int),
            "genre_id":       3,
            "type_droit_id":  td_id,
            "mesure":         "age_moyen_attribution",
            "valeur":         sub[col].round(2),
        }))

    out = pd.concat(rows, ignore_index=True)
    _truncate("Ages")
    n = to_sql(out, "Ages")
    return len(out)


# ── 4. fact.Montants ─────────────────────────────────────────────────────────

def load_montants() -> int:
    df = pd.read_parquet(PRO / "montant-global-de-la-retraite-au-31-decembre.parquet")
    df = df.dropna(subset=["annees_normees"])
    df["annee_id"] = df["annees_normees"].astype(int)

    col_nom  = "montant_mensuel_moyen_au_31_decembre_de_la_retraite_globale_en_euros"
    col_reel = "montant_equivalent_en_2025_montant_en_euros_corrige_de_l_inflation"

    rows = []
    for col, mesure in [(col_nom, "montant_global"), (col_reel, "montant_global_reel2025")]:
        sub = df[["annee_id", col]].dropna()
        rows.append(pd.DataFrame({
            "annee_id":     sub["annee_id"],
            "genre_id":     3,
            "type_droit_id": 4,   # Total
            "mesure":       mesure,
            "montant_euros": sub[col].round(2),
        }))

    out = pd.concat(rows, ignore_index=True)
    _truncate("Montants")
    n = to_sql(out, "Montants")
    return len(out)


# ── 5. fact.DureeAssurance ───────────────────────────────────────────────────

def load_durees() -> int:
    df = pd.read_parquet(PRO / "durees-moyennes-dassurance-limitees-et-non-limitees.parquet")
    df["annee_id"] = pd.to_numeric(
        df["annees"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce"
    )
    df = df.dropna(subset=["annee_id", "sexe"])
    df["annee_id"]  = df["annee_id"].astype(int)
    df["genre_id"]  = df["sexe"].map(GENRE_MAP)

    col_lim   = "durees_moyennes_d_assurance_en_trimestres"
    col_nonlim = "durees_moyennes_dassurance_en_trimestres_non_limitees"

    rows = []
    for col, limitee in [(col_lim, 1), (col_nonlim, 0)]:
        sub = df[["annee_id", "genre_id", col]].dropna()
        rows.append(pd.DataFrame({
            "annee_id":         sub["annee_id"],
            "genre_id":         sub["genre_id"],
            "type_droit_id":    1,   # Droits directs
            "limitee":          limitee,
            "duree_moyenne_trim": sub[col].round(1),
        }))

    out = pd.concat(rows, ignore_index=True)
    _truncate("DureeAssurance")
    n = to_sql(out, "DureeAssurance")
    return len(out)


# ── 6. ext.INSEE_PyramideAges ────────────────────────────────────────────────

def load_pyramide_ages() -> int:
    csv_path = Path("data/raw/external/donnees_pyramide_proj.csv")
    df = load_pyramide_from_csv(csv_path)

    out = (df[["annee", "age", "genre_code", "population", "source_fichier"]]
           .drop_duplicates(subset=["annee", "age", "genre_code"])
           .copy())

    with engine().begin() as conn:
        conn.execute(sa.text("DELETE FROM [ext].[INSEE_PyramideAges]"))

    rows = out.to_sql(
        name="INSEE_PyramideAges",
        schema="ext",
        con=engine(),
        if_exists="append",
        index=False,
        dtype={
            "annee":         sa.SmallInteger(),
            "age":           sa.SmallInteger(),
            "genre_code":    sa.CHAR(1),
            "population":    sa.BigInteger(),
            "source_fichier": sa.NVARCHAR(20),
        },
    )
    return len(out)


# ── 7. ext.DREES_PensionsMultiRegimes ───────────────────────────────────────

def load_drees_panorama() -> int:
    df = fetch_all_drees(download=False)

    out = df[["annee", "regime_id", "genre_code", "indicateur",
              "valeur", "unite", "source_fichier"]].copy()
    out["annee"]     = out["annee"].astype(int)
    out["regime_id"] = out["regime_id"].astype(int)
    out["valeur"]    = pd.to_numeric(out["valeur"], errors="coerce").round(4)
    out = out.dropna(subset=["valeur"])

    with engine().begin() as conn:
        conn.execute(sa.text(
            "DELETE FROM [ext].[DREES_PensionsMultiRegimes] "
            "WHERE source_fichier = 'DREES_PANORAMA_2025'"
        ))

    out.to_sql(
        name="DREES_PensionsMultiRegimes",
        schema="ext",
        con=engine(),
        if_exists="append",
        index=False,
        dtype={
            "annee":          sa.SmallInteger(),
            "regime_id":      sa.SmallInteger(),
            "genre_code":     sa.CHAR(1),
            "indicateur":     sa.NVARCHAR(50),
            "valeur":         sa.Numeric(12, 4),
            "unite":          sa.NVARCHAR(20),
            "source_fichier": sa.NVARCHAR(200),
        },
    )
    return len(out)


# ── Point d'entrée ────────────────────────────────────────────────────────────

def load_all() -> None:
    print("Préparation dim.CARSAT...")
    _ensure_carsat_sudest()

    loaders = [
        ("fact.RetraitesEffectifs",         load_effectifs),
        ("fact.Attributions",               load_attributions),
        ("fact.Ages",                       load_ages),
        ("fact.Montants",                   load_montants),
        ("fact.DureeAssurance",             load_durees),
        ("ext.INSEE_PyramideAges",          load_pyramide_ages),
        ("ext.DREES_PensionsMultiRegimes",  load_drees_panorama),
    ]
    total = 0
    for name, fn in loaders:
        try:
            n = fn()
            print(f"  {name:<35} → {n:>5} lignes chargées")
            total += n
        except Exception as e:
            print(f"  {name:<35} → ERREUR : {e}")

    print(f"\nTotal : {total} lignes insérées.")


if __name__ == "__main__":
    load_all()
