"""Teste les vues rpt.* et affiche quelques lignes de chaque."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path; sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
import sqlalchemy as sa; import pandas as pd
from src.db import engine

VIEWS = [
    "rpt.v_PensionVsInflation",
    "rpt.v_TauxRetraiteVsPopulation",
    "rpt.v_AgeMoyenVsReformes",
    "rpt.v_CompaisonRegimes",
    "rpt.v_DureeRetraiteEstimee",
    "rpt.v_ProjectionVsCOR",
    "rpt.v_DashboardPrincipal",
]

with engine().connect() as conn:
    for view in VIEWS:
        try:
            df = pd.read_sql(f"SELECT TOP 5 * FROM {view}", conn)
            print(f"\n{'='*60}")
            print(f"  {view}  ({len(df)} lignes TOP5)")
            print(f"{'='*60}")
            print(df.to_string(index=False))
        except Exception as e:
            print(f"\n[ERREUR] {view}: {e}")
