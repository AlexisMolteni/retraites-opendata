"""Met à jour meta.SourcesExternesLog avec toutes les sources chargées."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path; sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
import sqlalchemy as sa
from src.db import engine

nouvelles_entrees = [
    {
        "source": "INSEE",
        "indicateur": "Espérance de vie à 60 et 65 ans (H/F) — France métropolitaine 1946-2023",
        "url": "https://www.insee.fr/fr/statistiques/fichier/6524724/fm_dod_mortalite.xlsx",
        "min_a": 1946, "max_a": 2023, "nb": 312, "statut": "IMPORTE",
        "fichier": "fm_dod_mortalite.xlsx",
    },
    {
        "source": "DREES",
        "indicateur": "Niveau des pensions — pension brute mensuelle H/F/T 2004-2023 (Fiche 05)",
        "url": "https://drees.solidarites-sante.gouv.fr/sites/default/files/2025-07/Fiche%2005%20-%20Le%20niveau%20des%20pensions.xlsx",
        "min_a": 2004, "max_a": 2023, "nb": 60, "statut": "IMPORTE",
        "fichier": "drees_fiche05_niveau.xlsx",
    },
    {
        "source": "DREES",
        "indicateur": "Pension des nouveaux retraités vs ensemble en euros constants 2023 (Fiche 07)",
        "url": "https://drees.solidarites-sante.gouv.fr/sites/default/files/2025-07/Fiche%2007%20-%20La%20pension%20des%20nouveaux%20retrait%C3%A9s.xlsx",
        "min_a": 2004, "max_a": 2023, "nb": 36, "statut": "IMPORTE",
        "fichier": "drees_fiche07_nouveaux.xlsx",
    },
]

with engine().begin() as conn:
    for e in nouvelles_entrees:
        existing = conn.execute(sa.text(
            "SELECT COUNT(*) FROM meta.SourcesExternesLog WHERE source=:src AND indicateur=:ind"
        ).bindparams(src=e["source"], ind=e["indicateur"])).scalar()
        if existing == 0:
            conn.execute(sa.text("""
                INSERT INTO meta.SourcesExternesLog
                    (source, indicateur, url_telechargement, annee_donnees_min, annee_donnees_max,
                     nb_lignes, statut)
                VALUES (:src, :ind, :url, :min_a, :max_a, :nb, :st)
            """).bindparams(
                src=e["source"], ind=e["indicateur"], url=e["url"],
                min_a=e["min_a"], max_a=e["max_a"], nb=e["nb"], st=e["statut"]
            ))
            print(f"  INSERT : {e['source']} — {e['indicateur'][:60]}")
        else:
            conn.execute(sa.text("""
                UPDATE meta.SourcesExternesLog
                SET statut = :st, nb_lignes = :nb, date_import = SYSUTCDATETIME()
                WHERE source = :src AND indicateur = :ind
            """).bindparams(src=e["source"], ind=e["indicateur"], st=e["statut"], nb=e["nb"]))
            print(f"  UPDATE : {e['source']} — {e['indicateur'][:60]}")

    # Marquer pyramide comme IMPORTE avec nb_lignes
    conn.execute(sa.text("""
        UPDATE meta.SourcesExternesLog
        SET statut = 'IMPORTE', nb_lignes = 7199,
            annee_donnees_min = 1991, annee_donnees_max = 2070,
            date_import = SYSUTCDATETIME()
        WHERE source = 'INSEE' AND indicateur LIKE '%Pyramide%'
    """))

print("\nmeta.SourcesExternesLog mis à jour.")
