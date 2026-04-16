import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv('c:/EcoStream/.env')

WAQI_API_KEY = os.getenv("WAQI_API_KEY")
OWM_API_KEY = os.getenv("OWM_API_KEY")

city = "New Delhi"

print("--- WAQI API ---")
url = f"https://api.waqi.info/feed/{urllib.parse.quote(city)}/?token={WAQI_API_KEY}"
try:
    print(requests.get(url).json())
except Exception as e:
    print(f"WAQI Error: {e}")

print("\n--- OWM API ---")
url = f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(city)},IN&appid={OWM_API_KEY}&units=metric"
try:
    print(requests.get(url).json())
except Exception as e:
    print(f"OWM Error: {e}")
