import requests
import json

url = "https://trfetbxovhmbmwgbqdqm.supabase.co/rest/v1/daily_aqi_weather"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZmV0YnhvdmhtYm13Z2JxZHFtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM1NjY3MCwiZXhwIjoyMDkxOTMyNjcwfQ.XgrP4c5hniQJbSK87xpEru820e24K9gLebA2bBt-Gb8"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# Test record
record = {
    "city": "TestCity",
    "timestamp": "2026-04-22T12:00:00+00:00",
    "aqi": 50
}

print("Testing REST upload...")
try:
    response = requests.post(url, headers=headers, data=json.dumps([record]))
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
