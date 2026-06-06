from dotenv import load_dotenv; load_dotenv()
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.db import engine
import sqlalchemy as sa

with engine().connect() as conn:
    r = conn.execute(sa.text("""
        SELECT
            MIN(annee) AS annee_min,
            MAX(annee) AS annee_max,
            COUNT(DISTINCT annee) AS nb_annees,
            COUNT(DISTINCT age) AS nb_ages,
            COUNT(DISTINCT genre_code) AS nb_genres,
            COUNT(*) AS nb_total,
            SUM(CASE WHEN source_fichier = 'INSEE_OBS'  THEN 1 ELSE 0 END) AS obs,
            SUM(CASE WHEN source_fichier = 'INSEE_PROJ' THEN 1 ELSE 0 END) AS proj
        FROM ext.INSEE_PyramideAges
    """)).fetchone()
    print(f"Annees   : {r[0]} -> {r[1]} ({r[2]} annees)")
    print(f"Ages     : {r[3]} ages distincts (0-99)")
    print(f"Genres   : {r[4]} (H/F)")
    print(f"Total    : {r[5]} lignes")
    print(f"OBS      : {r[6]}   PROJ : {r[7]}")

    # Check population totale 2023 (derniere annee complete observee)
    r2 = conn.execute(sa.text("""
        SELECT genre_code, SUM(population)/1000000.0 AS pop_millions
        FROM ext.INSEE_PyramideAges
        WHERE annee = 2023
        GROUP BY genre_code
    """)).fetchall()
    print("\nPopulation 2023 (millions) :")
    for row in r2:
        print(f"  {row[0]} : {row[1]:.2f} M")
