-- Enable the UUID and PostGIS extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

CREATE TABLE IF NOT EXISTS daily_aqi_weather (
    -- Primary Key & Identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    city VARCHAR(100) NOT NULL,
    location GEOGRAPHY(POINT, 4326), -- Added for spatial correlation/distance calculations
    timestamp TIMESTAMPTZ NOT NULL,

    -- Air Quality Parameters
    aqi NUMERIC,
    pm25 NUMERIC,
    pm10 NUMERIC,
    o3 NUMERIC,
    no2 NUMERIC,
    so2 NUMERIC,
    co NUMERIC,
    aerosol_optical_depth NUMERIC, -- New: Satellite-derived haze indicator

    -- Weather Parameters (Core)
    temperature NUMERIC,
    temp_mean NUMERIC,             -- New: Replaces temp_min/max for better modeling
    temp_range NUMERIC,            -- New: Captures daily variation (max - min)
    feels_like NUMERIC,
    humidity NUMERIC,
    pressure NUMERIC,

    -- Wind & Atmosphere
    wind_speed NUMERIC,
    wind_deg NUMERIC,
    clouds NUMERIC,
    boundary_layer_height NUMERIC, -- New: Crucial for XAI (mixing height)
    precipitation NUMERIC,         -- New: Pollution wash-out factor
    solar_radiation NUMERIC,       -- New: Drives photochemical smog (O3)
    weather_condition VARCHAR(100),

    -- Temporal Indicators
    is_weekend BOOLEAN,            -- New: Proxy for traffic/industrial cycles

    -- Constraints
    UNIQUE(city, timestamp)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_city_timestamp ON daily_aqi_weather(city, timestamp);
CREATE INDEX IF NOT EXISTS idx_location ON daily_aqi_weather USING GIST(location);