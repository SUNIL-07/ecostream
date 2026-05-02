import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
password = "uyvZDV14xQmxsLnM"
project_id = "trfetbxovhmbmwgbqdqm"
# Try Mumbai pooler (IPv4)
pooler_host = "aws-0-ap-south-1.pooler.supabase.com"
user = f"postgres.{project_id}"
db_name = "postgres"

url = f"postgresql://{user}:{password}@{pooler_host}:6543/{db_name}?sslmode=require"

print(f"Testing connection to Mumbai Pooler: {pooler_host}")
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Success: {result.scalar()}")
except Exception as e:
    print(f"Failed: {e}")
