-- schema.sql
-- Create the daily_aqi_weather table to store environment metrics

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS daily_aqi_weather (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    city VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    pm25 NUMERIC,
    no2 NUMERIC,
    o3 NUMERIC,
    temperature NUMERIC,
    humidity NUMERIC,
    pressure NUMERIC,
    wind_speed NUMERIC,
    weather_condition VARCHAR(100),
    UNIQUE(city, timestamp)
);

-- Index for efficient time-series querying
CREATE INDEX IF NOT EXISTS idx_city_timestamp ON daily_aqi_weather(city, timestamp);
