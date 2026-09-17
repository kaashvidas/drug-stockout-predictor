"""
Loads the processed, real+checkpoint-constrained datasets into memory once at
startup. Read-heavy analytical data (facility registry, risk snapshots,
cascade stress, drug catalog, travel times) is served straight from these
pandas frames -- rerun the scripts/ and ml/ pipelines to refresh them.
Write-heavy operational data (users, redistribution approvals, audit log)
lives in SQLite (see db.py).
"""
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED = ROOT / "data" / "processed"
SYNTHETIC = ROOT / "data" / "synthetic"
RAW = ROOT / "data" / "raw"


@lru_cache
def load_facilities() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "facilities.csv")


@lru_cache
def load_current_risk_snapshot() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "current_risk_snapshot.csv")


@lru_cache
def load_cascade_snapshot() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "facility_cascade_snapshot.csv")


@lru_cache
def load_travel_times() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "travel_times.csv")


@lru_cache
def load_nlem_catalog() -> list[dict]:
    return json.loads((PROCESSED / "nlem_catalog.json").read_text(encoding="utf-8"))


@lru_cache
def load_cag_ground_truth() -> dict:
    return json.loads((PROCESSED / "cag_karnataka_ground_truth.json").read_text(encoding="utf-8"))


@lru_cache
def load_latest_weather_by_district() -> dict:
    """Most recent real Open-Meteo observation per district -- used to derate
    redistribution route feasibility under real heavy rain (ml/matching.py)."""
    df = pd.read_csv(RAW / "weather_daily.csv", parse_dates=["date"])
    latest = df.sort_values("date").groupby("district").tail(1)
    return latest.set_index("district")[["rain_mm", "temp_max_c"]].to_dict(orient="index")


@lru_cache
def load_validation_report() -> dict:
    path = PROCESSED / "validation_report.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


_daily_stock_df: pd.DataFrame | None = None


def load_daily_stock_for(facility_id: str, drug: str) -> pd.DataFrame:
    """Loaded lazily and filtered per-request (2.6M rows total; too large to
    hold fully materialized as separate copies per request, but small enough
    to filter directly with pyarrow predicate pushdown)."""
    df = pd.read_parquet(
        SYNTHETIC / "daily_stock.parquet",
        filters=[("facility_id", "==", facility_id), ("drug", "==", drug)],
    )
    return df.sort_values("date")


DRUG_CATEGORY_TO_PROGRAM = {
    "anti_tb": "Central TB Division",
    "envenomation": "NVBDCP (vector-borne & envenomation)",
    "maternal": "Reproductive & Child Health Programme",
    "thalassemia_chelation": "Dept. of Health & Family Welfare (Karnataka) -- Hemoglobinopathy Programme",
}

# Mirrors scripts/generate_synthetic_stock.py DRUG_BASKET (kept in sync there;
# duplicated here to avoid importing the generator script into the API process).
DRUG_TO_CATEGORY = {
    "Isoniazid": "anti_tb", "Rifampicin": "anti_tb", "Ethambutol": "anti_tb", "Pyrazinamide": "anti_tb",
    "Amoxicillin": "antibiotic", "Ciprofloxacin": "antibiotic", "Metronidazole": "antibiotic",
    "Azithromycin": "antibiotic", "Doxycycline": "antibiotic",
    "Paracetamol": "analgesic", "Ibuprofen": "analgesic", "Diclofenac": "analgesic",
    "Oral rehydration salts": "fluids", "Ringer lactate": "fluids",
    "Metformin": "chronic", "Amlodipine": "chronic", "Atenolol": "chronic",
    "Oxytocin": "maternal",
    "Snake Venom Antiserum": "envenomation",
    "Insulin (Soluble)": "diabetes",
    "Deferoxamine": "thalassemia_chelation", "Deferasirox": "thalassemia_chelation",
    "Deferiprone": "thalassemia_chelation", "Hydroxyurea": "thalassemia_chelation",
}


def scope_facilities(role: str, scope: str) -> pd.DataFrame:
    facilities = load_facilities()
    if role == "facility":
        return facilities[facilities["facility_id"] == scope]
    if role == "district":
        return facilities[facilities["district"] == scope]
    if role == "state":
        return facilities[facilities["state"] == scope]
    if role == "program":
        return facilities  # vertical programs see cross-state, filtered by drug elsewhere
    return facilities  # national


def scope_risk_snapshot(role: str, scope: str) -> pd.DataFrame:
    risk = load_current_risk_snapshot().copy()
    risk["drug_category"] = risk["drug"].map(DRUG_TO_CATEGORY)
    if role == "facility":
        return risk[risk["facility_id"] == scope]
    if role == "district":
        return risk[risk["district"] == scope]
    if role == "state":
        return risk[risk["state"] == scope]
    if role == "program":
        return risk[risk["drug_category"] == scope]
    return risk
