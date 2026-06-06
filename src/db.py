"""Moteur SQLAlchemy — connexion sécurisée via Azure Key Vault."""
import os
from functools import lru_cache

import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()
from src.vault import get_secret


@lru_cache(maxsize=1)
def engine() -> sa.Engine:
    server = os.getenv("SQL_SERVER")
    db     = os.getenv("SQL_DATABASE")
    user   = os.getenv("SQL_USER")
    driver = os.getenv("SQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server").replace(" ", "+")
    pwd    = get_secret(os.getenv("SQL_SECRET_NAME", "SQL-SACredential"))
    url    = (
        f"mssql+pyodbc://{user}:{pwd}@{server}/{db}"
        f"?driver={driver}&TrustServerCertificate=yes"
    )
    return sa.create_engine(url, fast_executemany=True)
