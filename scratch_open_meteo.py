import requests

lat, lon = 28.6139, 77.2090 # New Delhi

url_oq = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi&start_date=2020-01-01&end_date=2020-01-02"

res = requests.get(url_oq)
print("AQI 2020 Data:", res.status_code, res.text[:200])

url_weather = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2020-01-01&end_date=2020-01-02&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation,surface_pressure,cloud_cover,wind_speed_10m,wind_direction_10m"
res_w = requests.get(url_weather)
print("Weather 2020 Data:", res_w.status_code, res_w.text[:200])
