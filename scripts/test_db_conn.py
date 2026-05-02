import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("SUPABASE_DB_URL")
# Try the pooler port
pooler_url = db_url.replace(":5432/", ":6543/")
if "?sslmode" not in pooler_url:
    pooler_url += "?sslmode=require"

print(f"Testing connection to: {pooler_url}")
try:
    engine = create_engine(pooler_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Success: {result.scalar()}")
except Exception as e:
    print(f"Failed: {e}")
