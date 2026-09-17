"""
Leading-indicator fusion (build guide Section 05):

    demand_multiplier(drug, district, week) = baseline * PROD_k rule_k(district, week)

Rule table maps real Open-Meteo weather signals to NLEM drug categories.
(IDSP outbreak-category rules are listed but disabled by default -- see
docs/DATA_SOURCES.md: IDSP's live bulletin could not be fetched
programmatically in this project, so no outbreak-derived multiplier is
applied unless a real IDSP feed is wired in via `idsp_signal`.)
"""
from dataclasses import dataclass


@dataclass
class WeatherSignal:
    rain_mm: float
    temp_max_c: float


def demand_multiplier(drug_category: str, weather: WeatherSignal, idsp_signal: dict | None = None) -> float:
    mult = 1.0

    if drug_category == "envenomation":
        mult *= 1.0 + min(weather.rain_mm / 15.0, 3.0)
    if drug_category == "fluids":
        mult *= 1.0 + min(weather.rain_mm / 25.0, 1.5) + max(0.0, (weather.temp_max_c - 38) / 10.0)
    if drug_category == "anti_tb":
        mult *= 1.0 + min(weather.rain_mm / 60.0, 0.3)

    if idsp_signal:
        outbreak_category = idsp_signal.get("category")
        severity = idsp_signal.get("severity", 0.0)
        RULE_MAP = {
            "diarrheal": "fluids",
            "vector_borne": "antibiotic",
            "respiratory": "antibiotic",
        }
        if RULE_MAP.get(outbreak_category) == drug_category:
            mult *= 1.0 + severity

    return mult
