"""Diagnostique et corrige les vues rpt.* selon les données réelles."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path; sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
import sqlalchemy as sa; import pandas as pd
from src.db import engine

with engine().connect() as conn:
    # dim.TypeDroit
    df = pd.read_sql("SELECT * FROM dim.TypeDroit", conn)
    print("=== dim.TypeDroit ==="); print(df.to_string(index=False))

    # fact.Montants - genre et type_droit_id distribution
    df2 = pd.read_sql("""
        SELECT m.mesure, m.type_droit_id, d.code, g.code AS genre,
               COUNT(*) AS n, MIN(a.annee) AS min_a, MAX(a.annee) AS max_a,
               MIN(m.montant_euros) AS min_eur, MAX(m.montant_euros) AS max_eur
        FROM fact.Montants m
        JOIN dim.Annee a ON a.annee_id = m.annee_id
        JOIN dim.TypeDroit d ON d.type_droit_id = m.type_droit_id
        JOIN dim.Genre g ON g.genre_id = m.genre_id
        GROUP BY m.mesure, m.type_droit_id, d.code, g.code
        ORDER BY m.mesure, d.code, g.code
    """, conn)
    print("\n=== fact.Montants détail ==="); print(df2.to_string(index=False))

    # v_AgeMoyenAttribution dépendance
    try:
        df3 = pd.read_sql("SELECT TOP 3 * FROM rpt.v_AgeMoyenAttribution", conn)
        print("\n=== rpt.v_AgeMoyenAttribution (3 lignes) ==="); print(df3.to_string(index=False))
    except Exception as e:
        print(f"\n[ERREUR] v_AgeMoyenAttribution: {e}")
