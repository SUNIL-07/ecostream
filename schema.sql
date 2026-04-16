CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS daily_aqi_weather (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    city VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    aqi NUMERIC,
    pm25 NUMERIC,
    pm10 NUMERIC,
    o3 NUMERIC,
    no2 NUMERIC,
    so2 NUMERIC,
    co NUMERIC,
    temperature NUMERIC,
    temp_min NUMERIC,
    temp_max NUMERIC,
    feels_like NUMERIC,
    humidity NUMERIC,
    pressure NUMERIC,
    wind_speed NUMERIC,
    wind_deg NUMERIC,
    clouds NUMERIC,
    weather_condition VARCHAR(100),
    UNIQUE(city, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_city_timestamp ON daily_aqi_weather(city, timestamp);
