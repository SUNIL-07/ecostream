import requests
import pandas as pd

weather_vars = 'temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code,precipitation,shortwave_radiation,visibility,uv_index,boundary_layer_height'
aqi_vars = 'us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,aerosol_optical_depth,uv_index'

years = range(2016, 2026)
results = []
print('Testing New Delhi (Jan 1-5 for each year)...')

for y in years:
    start = f'{y}-01-01'
    end = f'{y}-01-05'
    
    # Weather
    res_w = requests.get(f'https://archive-api.open-meteo.com/v1/archive?latitude=28.6&longitude=77.2&start_date={start}&end_date={end}&hourly={weather_vars}')
    df_w = pd.DataFrame(res_w.json().get('hourly', {}))
    
    # AQI
    res_a = requests.get(f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude=28.6&longitude=77.2&start_date={start}&end_date={end}&hourly={aqi_vars}')
    df_a = pd.DataFrame(res_a.json().get('hourly', {}))
    
    total_rows = len(df_w)
    result_w = {k: f'{df_w[k].notnull().sum()}/{total_rows}' for k in df_w.columns if k != 'time'}
    
    total_rows_a = len(df_a)
    result_a = {}
    if not df_a.empty:
        result_a = {f'aqi_{k}': f'{df_a[k].notnull().sum()}/{total_rows_a}' for k in df_a.columns if k != 'time'}
    else:
        result_a = {f'aqi_{k}': '0/0' for k in aqi_vars.split(',')}
        
    row = {'year': y, **result_w, **result_a}
    results.append(row)
    print(f'Year {y} tested.')

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
df_res = pd.DataFrame(results)
df_res.to_csv('openmeteo_availability.csv', index=False)
print('\nSaved to openmeteo_availability.csv')
