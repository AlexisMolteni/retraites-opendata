"""
Chargement des données dans SQL Server.
Les mots de passe sont récupérés depuis Azure Key Vault à l'exécution.
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import sqlalchemy as sa

from src.db import engine
from src.fetch_external import load_esperance_vie, load_pyramide_from_csv
from src.fetch_drees import fetch_all_drees


# ─── Espérance de vie ─────────────────────────────────────────────────────────

def load_esperance_vie_sql() -> int:
    df = load_esperance_vie()
    if df.empty:
        print("Aucune donnée d'espérance de vie trouvée.")
        return 0

    out = df[["annee", "genre_code", "age_reference", "esperance_annees", "type_mesure", "source_fichier"]].copy()
    out = out.drop_duplicates(subset=["annee", "genre_code", "age_reference", "type_mesure"])

    with engine().begin() as conn:
        conn.execute(sa.text(
            "DELETE FROM [ext].[INSEE_EsperanceVie] WHERE source_fichier = 'INSEE_fm_dod_mortalite'"
        ))
        out.to_sql(
            "INSEE_EsperanceVie", conn, schema="ext",
            if_exists="append", index=False,
            dtype={
                "annee":          sa.SmallInteger(),
                "genre_code":     sa.CHAR(1),
                "age_reference":  sa.SmallInteger(),
                "esperance_annees": sa.Numeric(5, 2),
                "type_mesure":    sa.NVARCHAR(20),
                "source_fichier": sa.NVARCHAR(200),
            },
        )
    n = len(out)
    print(f"ext.INSEE_EsperanceVie : {n} lignes chargées")
    return n


# ─── Pyramide des âges ────────────────────────────────────────────────────────

def load_pyramide_ages() -> int:
    csv_path = Path("data/raw/external/donnees_pyramide_proj.csv")
    if not csv_path.exists():
        print(f"Fichier absent : {csv_path}")
        return 0

    df = load_pyramide_from_csv(csv_path)
    out = df[["annee", "age", "genre_code", "population", "source_fichier"]].copy()
    out = out.drop_duplicates(subset=["annee", "age", "genre_code"])

    with engine().begin() as conn:
        conn.execute(sa.text("DELETE FROM [ext].[INSEE_PyramideAges]"))
        out.to_sql(
            "INSEE_PyramideAges", conn, schema="ext",
            if_exists="append", index=False,
            dtype={
                "annee":          sa.SmallInteger(),
                "age":            sa.SmallInteger(),
                "genre_code":     sa.CHAR(1),
                "population":     sa.BigInteger(),
                "source_fichier": sa.NVARCHAR(200),
            },
        )
    n = len(out)
    print(f"ext.INSEE_PyramideAges : {n} lignes chargées")
    return n


# ─── DREES nouvelles fiches ───────────────────────────────────────────────────

def load_drees_nouvelles_fiches() -> int:
    """Charge fiche 05 (niveau pensions) et fiche 07 (nouveaux retraités)."""
    df = fetch_all_drees(include_existing=False)
    if df.empty:
        print("Aucune donnée DREES à charger.")
        return 0

    out = df[["annee", "regime_id", "genre_code", "indicateur", "valeur", "unite", "source_fichier"]].copy()

    indicateurs = out["indicateur"].unique().tolist()

    with engine().begin() as conn:
        for ind in indicateurs:
            conn.execute(sa.text(
                "DELETE FROM [ext].[DREES_PensionsMultiRegimes] WHERE indicateur = :ind"
            ).bindparams(ind=ind))

        out.to_sql(
            "DREES_PensionsMultiRegimes", conn, schema="ext",
            if_exists="append", index=False,
            dtype={
                "annee":          sa.SmallInteger(),
                "regime_id":      sa.SmallInteger(),
                "genre_code":     sa.CHAR(1),
                "indicateur":     sa.NVARCHAR(50),
                "valeur":         sa.Numeric(12, 2),
                "unite":          sa.NVARCHAR(20),
                "source_fichier": sa.NVARCHAR(200),
            },
        )
    n = len(out)
    print(f"ext.DREES_PensionsMultiRegimes : {n} nouvelles lignes chargées")
    for ind in indicateurs:
        cnt = len(out[out["indicateur"] == ind])
        print(f"  {ind}: {cnt} lignes")
    return n


# ─── Mise à jour du log ───────────────────────────────────────────────────────

def update_sources_log() -> None:
    updates = [
        ("INSEE", "Pyramide des âges par sexe et groupe d'âge",      "IMPORTE", 7199),
        ("INSEE", "Espérance de vie à divers âges",                   "IMPORTE", None),
        ("DREES", "Les retraités et les retraites — édition annuelle", "IMPORTE", None),
    ]
    with engine().begin() as conn:
        for source, indicateur, statut, nb in updates:
            conn.execute(sa.text(
                "UPDATE meta.SourcesExternesLog SET statut = :st"
                + (", nb_lignes = :nb" if nb is not None else "")
                + ", date_import = SYSUTCDATETIME()"
                + " WHERE source = :src AND indicateur = :ind"
            ).bindparams(**{
                "st": statut,
                "src": source,
                "ind": indicateur,
                **({"nb": nb} if nb is not None else {}),
            }))
    print("meta.SourcesExternesLog mis à jour")


# ─── Exécution directe ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Chargement espérance de vie INSEE ===")
    load_esperance_vie_sql()

    print("\n=== Chargement nouvelles fiches DREES ===")
    load_drees_nouvelles_fiches()

    print("\n=== Mise à jour log sources ===")
    update_sources_log()

    print("\nTerminé.")
