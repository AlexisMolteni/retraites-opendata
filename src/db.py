"""Moteur SQLAlchemy — connexion sécurisée via Azure Key Vault."""
import os
from functools import lru_cache

import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()
from src.vault import get_secret

SQL_SERVER   = os.getenv("SQL_SERVER",   r"localhost\MSSQLSERVER2022")
SQL_DATABASE = os.getenv("SQL_DATABASE", "RetraitesOpenData")
SQL_USER     = os.getenv("SQL_USER",     "sa")
SQL_SECRET   = os.getenv("SQL_SECRET_NAME", "SQL-SACredential")
ODBC_DRIVER  = os.getenv("SQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")


@lru_cache(maxsize=1)
def engine() -> sa.Engine:
    pwd = get_secret(SQL_SECRET)
    conn_str = (
        f"mssql+pyodbc://{SQL_USER}:{pwd}@{SQL_SERVER}/{SQL_DATABASE}"
        f"?driver={ODBC_DRIVER.replace(' ', '+')}"
        f"&TrustServerCertificate=yes"
        f"&Encrypt=yes"
    )
    return sa.create_engine(conn_str, fast_executemany=True)


def read_sql(query: str, **kwargs) -> pd.DataFrame:
    """Exécute une requête SELECT et renvoie un DataFrame (decimal → float64)."""
    with engine().connect() as conn:
        df = pd.read_sql(sa.text(query), conn, **kwargs)
    for col in df.select_dtypes(include="object").columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df


def to_sql(df: pd.DataFrame, table: str, schema: str = "fact",
           if_exists: str = "append", **kwargs) -> int:
    """Insère un DataFrame dans une table SQL et retourne le nombre de lignes."""
    rows = df.to_sql(
        name=table, schema=schema, con=engine(),
        if_exists=if_exists, index=False, **kwargs,
    )
    return rows or 0
