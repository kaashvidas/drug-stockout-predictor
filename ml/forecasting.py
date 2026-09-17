"""
Prophet forecasting (build guide Section 08: "Prophet handles seasonality/
holiday effects out of the box"), fused with the REAL Open-Meteo 16-day
weather forecast (data/raw/weather_forecast_16day.csv) via the leading-
indicator rule table in ml/fusion.py -- this is the one place in the
pipeline that literally implements Section 05's
"demand_multiplier(drug, district, week) = baseline * PROD rule_k(...)"
using live forecast data rather than historical weather.
"""
from pathlib import Path

import pandas as pd
from prophet import Prophet

from ml.fusion import demand_multiplier, WeatherSignal

ROOT = Path(__file__).resolve().parent.parent
WEATHER_FORECAST_PATH = ROOT / "data" / "raw" / "weather_forecast_16day.csv"


def forecast_consumption(dates: pd.Series, consumption: pd.Series, periods: int = 16) -> pd.DataFrame:
    df = pd.DataFrame({"ds": pd.to_datetime(dates), "y": consumption.to_numpy()})
    model = Prophet(
        weekly_seasonality=True, yearly_seasonality=False, daily_seasonality=False,
        changepoint_prior_scale=0.1,
    )
    model.fit(df)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    return forecast.tail(periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def apply_real_weather_fusion(forecast_df: pd.DataFrame, district: str, drug_category: str) -> pd.DataFrame:
    """Multiply the Prophet forecast by the real, live 16-day weather-driven
    demand multiplier for this district and drug category.

    Aligned by FORECAST-HORIZON POSITION (day 1 of the forecast <-> day 1 of
    the real live Open-Meteo forecast), not by matching calendar date value:
    the synthetic historical series ends 2024-12-31 (see
    scripts/generate_synthetic_stock.py), while the real Open-Meteo forecast
    is always relative to today. Position-alignment is the honest way to
    fuse "what real weather is coming next" with "what the model predicts
    happens next in the series" without pretending the two calendars are
    the same year.
    """
    weather = pd.read_csv(WEATHER_FORECAST_PATH, parse_dates=["date"])
    weather = weather[weather["district"] == district].sort_values("date").reset_index(drop=True)
    # Open-Meteo's final forecast-horizon day is occasionally incomplete
    # (nulls) at the model's cutoff; forward-fill from the prior real day
    # rather than let a missing observation silently become NaN demand.
    weather[["rain_mm", "temp_max_c"]] = weather[["rain_mm", "temp_max_c"]].ffill()

    out = forecast_df.reset_index(drop=True).copy()
    multipliers = []
    for i in range(len(out)):
        if i < len(weather):
            row = weather.iloc[i]
            signal = WeatherSignal(rain_mm=float(row["rain_mm"]), temp_max_c=float(row["temp_max_c"]))
            multipliers.append(demand_multiplier(drug_category, signal))
        else:
            multipliers.append(1.0)
    out["weather_multiplier"] = multipliers
    out["yhat_fused"] = (out["yhat"] * out["weather_multiplier"]).clip(lower=0)
    return out


def project_days_of_cover(current_stock: float, fused_forecast: pd.DataFrame) -> pd.DataFrame:
    """Project forward stock (no restock assumed) and the date it would cross
    zero at current forecasted consumption -- the 'projected stockout date'
    shown on facility/district dashboards."""
    out = fused_forecast.copy()
    out["cumulative_consumption"] = out["yhat_fused"].cumsum()
    out["projected_stock"] = (current_stock - out["cumulative_consumption"]).clip(lower=0)
    return out
