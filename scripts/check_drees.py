"""Vérifie le contenu de ext.DREES_PensionsMultiRegimes."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
import sqlalchemy as sa
import pandas as pd

server = os.getenv("SQL_SERVER"); db = os.getenv("SQL_DATABASE")
user   = os.getenv("SQL_USER"); driver = os.getenv("SQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server").replace(" ", "+")
pwd    = get_secret(os.getenv("SQL_SECRET_NAME", "SQL-SACredential"))
engine = sa.create_engine(f"mssql+pyodbc://{user}:{pwd}@{server}/{db}?driver={driver}&TrustServerCertificate=yes")

with engine.connect() as c:
    df = pd.read_sql("SELECT indicateur, genre_code, COUNT(*) AS n, MIN(annee) AS min_a, MAX(annee) AS max_a FROM ext.DREES_PensionsMultiRegimes GROUP BY indicateur, genre_code ORDER BY indicateur, genre_code", c)
    print(df.to_string())
