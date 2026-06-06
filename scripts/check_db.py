"""Vérifie l'état des tables dans RetraitesOpenData."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()
from src.vault import get_secret
import sqlalchemy as sa

server = os.getenv("SQL_SERVER")
db     = os.getenv("SQL_DATABASE")
user   = os.getenv("SQL_USER")
driver = os.getenv("SQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server").replace(" ", "+")
pwd    = get_secret(os.getenv("SQL_SECRET_NAME", "SQL-SACredential"))

conn_str = f"mssql+pyodbc://{user}:{pwd}@{server}/{db}?driver={driver}&TrustServerCertificate=yes"
engine = sa.create_engine(conn_str)

SQL = """
SELECT s.name + '.' + t.name AS tbl, p.rows AS nb
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)
WHERE s.name IN ('ext','meta','fact','dim')
ORDER BY s.name, t.name
"""

with engine.connect() as conn:
    rows = conn.execute(sa.text(SQL)).fetchall()
    for r in rows:
        print(f"{r[0]:<50s} {r[1]:>8} lignes")
