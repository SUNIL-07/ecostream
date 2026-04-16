import os
import pandas as pd
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.dialects.postgresql import insert
from dotenv import load_dotenv

# Load env safely
try:
    load_dotenv('../.env')
except:
    pass
    
try:
    load_dotenv('.env')
except:
    pass

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

file_path = 'artefacts/10yr_historical_data.csv'
if not os.path.exists(file_path):
    raise FileNotFoundError(f"Missing: {file_path}")

df = pd.read_csv(file_path)

# Pandas nan -> None for postgresql inserts natively
df = df.where(pd.notnull(df), None)

print(f"Starting bulk upload of {len(df)} records into Supabase...")

engine = create_engine(SUPABASE_DB_URL)
metadata = MetaData()
table = Table('daily_aqi_weather', metadata, autoload_with=engine)

records = df.to_dict(orient='records')
chunk_size = 2000

with engine.begin() as conn:
    for i in range(0, len(records), chunk_size):
        chunk = records[i : i + chunk_size]
        stmt = insert(table).values(chunk)
        # Bypassing the primary key uuid since default uuid_generate() kicks in automatically
        # Safely ignore any duplicate dates using constraints
        stmt = stmt.on_conflict_do_nothing(index_elements=['city', 'timestamp'])
        conn.execute(stmt)
        print(f"  -> Bulk upserted rows {i} to {i + len(chunk)}")

print("\n[✓] Historical Database Injection Fully Completed.")
