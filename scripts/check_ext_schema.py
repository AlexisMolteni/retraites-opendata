from dotenv import load_dotenv; load_dotenv()
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.db import engine
import sqlalchemy as sa
with engine().connect() as conn:
    r = conn.execute(sa.text(
        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME IN ('ext','meta')"
    )).fetchall()
    print("Schemas:", [x[0] for x in r])
    r2 = conn.execute(sa.text(
        "SELECT TABLE_SCHEMA+'.'+TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='ext' ORDER BY TABLE_NAME"
    )).fetchall()
    print("Tables ext:", [x[0] for x in r2])
