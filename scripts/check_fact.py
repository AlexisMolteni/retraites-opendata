"""Vérifie le contenu des tables fact.*"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path; sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
import sqlalchemy as sa; import pandas as pd
from src.db import engine

with engine().connect() as conn:
    # fact.Montants - mesures et type_droit
    df = pd.read_sql("""
        SELECT m.mesure, d.code AS type_droit, COUNT(*) AS n, MIN(a.annee) AS min_a, MAX(a.annee) AS max_a
        FROM fact.Montants m
        JOIN dim.Annee a ON a.annee_id = m.annee_id
        JOIN dim.TypeDroit d ON d.type_droit_id = m.type_droit_id
        GROUP BY m.mesure, d.code ORDER BY m.mesure, d.code
    """, conn)
    print("=== fact.Montants ===")
    print(df.to_string(index=False))

    # fact.RetraitesEffectifs - echantillon
    df2 = pd.read_sql("""
        SELECT TOP 5 a.annee, g.code AS genre, c.code AS carsat, f.nb_retraites
        FROM fact.RetraitesEffectifs f
        JOIN dim.Annee a ON a.annee_id = f.annee_id
        JOIN dim.Genre g ON g.genre_id = f.genre_id
        JOIN dim.CARSAT c ON c.carsat_id = f.carsat_id
        WHERE c.code = 'TOTAL'
        ORDER BY a.annee
    """, conn)
    print("\n=== fact.RetraitesEffectifs (TOTAL, 5 premières années) ===")
    print(df2.to_string(index=False))

    # Vérif nb lignes par table fact
    df3 = pd.read_sql("""
        SELECT s.name+'.'+t.name AS tbl, p.rows AS nb
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1)
        WHERE s.name = 'fact'
    """, conn)
    print("\n=== Toutes les tables fact.* ===")
    print(df3.to_string(index=False))
