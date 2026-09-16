"""
Fetch REAL historical daily weather for each district centroid from Open-Meteo
(free, keyless, real archive API -- Tier-1 source per the build guide).

Used downstream to derive real monsoon-onset / heatwave signals that feed the
leading-indicator demand-fusion rules (e.g. monsoon onset -> anti-snake-venom
demand multiplier).
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

FACILITIES = Path(__file__).resolve().parent.parent / "data" / "processed" / "facilities.csv"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "weather_daily.csv"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

START_DATE = "2023-01-01"
END_DATE = "2024-12-31"

DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum"


def district_centroids(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["state", "district"]).agg(lat=("lat", "mean"), lon=("lon", "mean")).reset_index()


def fetch_history(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": DAILY_VARS,
        "timezone": "Asia/Kolkata",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_forecast(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARS,
        "forecast_days": 16,
        "timezone": "Asia/Kolkata",
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    fac = pd.read_csv(FACILITIES)
    centroids = district_centroids(fac)

    all_rows = []
    for _, row in centroids.iterrows():
        print(f"Fetching weather history for {row['district']}, {row['state']} ...")
        data = fetch_history(row["lat"], row["lon"])
        daily = data["daily"]
        n = len(daily["time"])
        for i in range(n):
            all_rows.append(
                {
                    "district": row["district"],
                    "state": row["state"],
                    "date": daily["time"][i],
                    "temp_max_c": daily["temperature_2m_max"][i],
                    "temp_min_c": daily["temperature_2m_min"][i],
                    "precip_mm": daily["precipitation_sum"][i],
                    "rain_mm": daily["rain_sum"][i],
                }
            )
        time.sleep(1)

    out = pd.DataFrame(all_rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} real daily weather rows to {OUT_PATH}")

    # Also grab a live 16-day forecast per district for the "leading indicator" demo
    fc_rows = []
    for _, row in centroids.iterrows():
        data = fetch_forecast(row["lat"], row["lon"])
        daily = data["daily"]
        n = len(daily["time"])
        for i in range(n):
            fc_rows.append(
                {
                    "district": row["district"],
                    "state": row["state"],
                    "date": daily["time"][i],
                    "temp_max_c": daily["temperature_2m_max"][i],
                    "temp_min_c": daily["temperature_2m_min"][i],
                    "precip_mm": daily["precipitation_sum"][i],
                    "rain_mm": daily["rain_sum"][i],
                }
            )
        time.sleep(1)
    fc_out = pd.DataFrame(fc_rows)
    fc_path = OUT_PATH.parent / "weather_forecast_16day.csv"
    fc_out.to_csv(fc_path, index=False)
    print(f"Wrote {len(fc_out)} real forecast rows to {fc_path}")


if __name__ == "__main__":
    main()
