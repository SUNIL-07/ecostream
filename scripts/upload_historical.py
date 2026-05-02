import os
import sys
import pandas as pd
import requests
import json
import time
from pathlib import Path

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

# ─── Configuration ──────────────────────────────────────────
# Hardcoding keys for now as they were fetched via Management API due to local network issues
SUPABASE_URL = "https://trfetbxovhmbmwgbqdqm.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZmV0YnhvdmhtYm13Z2JxZHFtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM1NjY3MCwiZXhwIjoyMDkxOTMyNjcwfQ.XgrP4c5hniQJbSK87xpEru820e24K9gLebA2bBt-Gb8"
TABLE_NAME = "daily_aqi_weather"

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?on_conflict=city,timestamp"

# ─── Load CSV ────────────────────────────────────────────────
file_path = os.path.join(os.path.dirname(__file__), '..', 'artefacts', '10yr_hourly_timeline.csv')
file_path = os.path.normpath(file_path)

if not os.path.exists(file_path):
    file_path = os.path.join('artefacts', '10yr_hourly_timeline.csv')

if not os.path.exists(file_path):
    print(f"ERROR: CSV file not found at: {file_path}")
    sys.exit(1)

print(f"Reading CSV from: {file_path}")
df = pd.read_csv(file_path)
print(f"  Total rows loaded: {len(df)}")

# ─── Data Preparation ───────────────────────────────────────
df = df.dropna()
# Ensure timestamp is ISO format
df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

# Convert NaN to None (null) for JSON
df = df.where(pd.notnull(df), None)

records = df.to_dict(orient='records')

# ─── REST Upload ─────────────────────────────────────────────
headers = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates" # UPSERT logic
}

chunk_size = 1000 # Smaller chunks for REST API reliability
total_records = len(records)
print(f"\nStarting REST upload of {total_records} records to Supabase...")

success_count = 0
fail_count = 0

for i in range(0, total_records, chunk_size):
    chunk = records[i:i + chunk_size]
    try:
        response = requests.post(REST_URL, headers=headers, data=json.dumps(chunk), timeout=60)
        if response.status_code in [200, 201, 204]:
            success_count += len(chunk)
            print(f"  -> Uploaded rows {i} to {i + len(chunk)} (Status: {response.status_code})")
        else:
            print(f"  -> FAILED rows {i} to {i + len(chunk)}: {response.status_code} - {response.text[:200]}")
            fail_count += len(chunk)
    except Exception as e:
        print(f"  -> EXCEPTION on rows {i} to {i + len(chunk)}: {e}")
        fail_count += len(chunk)
    
    # Small sleep to be nice to the API
    time.sleep(0.5)

print(f"\n{'='*60}")
print(f"UPLOAD SUMMARY")
print(f"  Successfully uploaded: {success_count}")
print(f"  Failed:                {fail_count}")
print(f"{'='*60}")
