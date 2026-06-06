"""
Connexion SQL Server via SQLAlchemy.
Le mot de passe SA est récupéré depuis Azure Key Vault à la demande.
"""
import os
from functools import lru_cache
import sqlalchemy as sa
from src.vault import get_secret

SQL_SERVER   = os.getenv("SQL_SERVER",   r"localhost\MSSQLSERVER2022")
SQL_DATABASE = os.getenv("SQL_DATABASE", "RetraitesOpenData")
SQL_USER     = os.getenv("SQL_USER",     "sa")
SQL_SECRET   = os.getenv("SQL_SECRET_NAME", "SQL-SACredential")

# Pilote ODBC — SQL Server 2022 → ODBC Driver 18
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


def read_sql(query: str, **kwargs):
    import pandas as pd
    with engine().connect() as conn:
        df = pd.read_sql(sa.text(query), conn, **kwargs)
    # pyodbc retourne decimal.Decimal pour les colonnes DECIMAL/NUMERIC ;
    # on force la conversion en float64 pour compatibilité matplotlib/numpy.
    for col in df.select_dtypes(include="object").columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df


def to_sql(df, table: str, schema: str = "fact", if_exists: str = "append", **kwargs) -> int:
    rows = df.to_sql(
        name=table,
        schema=schema,
        con=engine(),
        if_exists=if_exists,
        index=False,
        **kwargs
    )
    return rows or 0
