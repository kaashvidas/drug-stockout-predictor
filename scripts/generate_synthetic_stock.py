"""
Tier-3 generator: daily per-facility-drug stock levels, for the real
Karnataka government-facility dataset.

WHY THIS EXISTS: no public source in India publishes live, day-by-day,
per-facility medicine stock counts (build guide Section 04; confirmed absent
in this repo's own data hunt -- see docs/DATA_SOURCES.md). This script is the
one place in the whole pipeline that generates rather than fetches data, and
it is grounded in real numbers at every constraint point, not free-running:

1. Facility identities (government hospitals/PHCs/CHCs), districts, and drug
   names are 100% real (Tier 1) -- see scripts/fetch_karnataka_facilities.py.
2. Each facility-drug pair's long-run stockout-rate parameter is SAMPLED FROM
   THE EMPIRICAL DISTRIBUTION of real, independently-verified CAG Karnataka
   audit percentages (data/processed/cag_karnataka_ground_truth.json) -- not
   an arbitrary made-up range. Facilities in the audit's own 5 real
   "test-checked" districts (Ballari, Bengaluru Urban, Dharwad, Kolar,
   Mysuru) are biased toward THAT district's own real reported shortfall
   rate rather than the statewide average.
3. Deferoxamine (Desferal) -- across EVERY Karnataka facility -- is
   hard-constrained to a chronic near-zero stock level for the entire
   window, matching the real, dated, multi-source documented fact that this
   drug has been absent from government hospitals since 2020, was still
   the subject of an unresolved Karnataka High Court PIL as of September
   2021, and was still missing (two failed KSMSCL tenders) as of October
   2023. This is a deliberately different failure SHAPE from a crisis-and-
   recovery arc: persistent structural zero, not a dip that gets fixed.
4. Weather-sensitive drug categories (Snake Venom Antiserum, ORS, Ringer
   lactate, anti-TB) are driven by the REAL Open-Meteo rain_mm/temp series
   per district, not a random seasonal curve.

Only the day-to-day interpolation between these real anchors is generated.
Every array this script writes is labeled "reconstructed" downstream; see
frontend/src/components/ReconstructedBadge.tsx.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FACILITIES_PATH = ROOT / "data" / "processed" / "facilities.csv"
WEATHER_PATH = ROOT / "data" / "raw" / "weather_daily.csv"
NLEM_PATH = ROOT / "data" / "processed" / "nlem_catalog.json"
CAG_PATH = ROOT / "data" / "processed" / "cag_karnataka_ground_truth.json"
OUT_PATH = ROOT / "data" / "synthetic" / "daily_stock.parquet"
OUT_CSV_SAMPLE = ROOT / "data" / "synthetic" / "daily_stock_sample.csv"

START_DATE = pd.Timestamp("2023-01-01")
END_DATE = pd.Timestamp("2024-12-31")

# The 5 real districts the CAG audit itself test-checked (Table 4.5) --
# their real supply-shortfall percentages bias facilities in these districts
# specifically, rather than treating every district identically.
CAG_TEST_CHECKED_DISTRICT_SHORTFALL_PCT = {
    "Ballari": 0.6535, "Bengaluru Urban": 0.6705, "Dharwad": 0.6790,
    "Kolar": 0.6693, "Mysuru": 0.6916,
}

# Real drug basket. The first 8 categories are verified present in the
# parsed NLEM 2022 catalog (data/processed/nlem_catalog.json). The
# thalassemia_chelation category is the deliberate exception, documented in
# cag_karnataka_ground_truth.json: these are real drug names sourced from
# court/news reporting specifically because their ABSENCE from NLEM is part
# of the real story.
DRUG_BASKET = {
    "anti_tb": ["Isoniazid", "Rifampicin", "Ethambutol", "Pyrazinamide"],
    "antibiotic": ["Amoxicillin", "Ciprofloxacin", "Metronidazole", "Azithromycin", "Doxycycline"],
    "analgesic": ["Paracetamol", "Ibuprofen", "Diclofenac"],
    "fluids": ["Oral rehydration salts", "Ringer lactate"],
    "chronic": ["Metformin", "Amlodipine", "Atenolol"],
    "maternal": ["Oxytocin"],
    "envenomation": ["Snake Venom Antiserum"],
    "diabetes": ["Insulin (Soluble)"],
    "thalassemia_chelation": ["Deferoxamine", "Deferasirox", "Deferiprone", "Hydroxyurea"],
}
ALL_DRUGS = [d for group in DRUG_BASKET.values() for d in group]
CHRONIC_SHORTAGE_DRUGS = {"Deferoxamine", "Deferasirox", "Deferiprone"}  # NOT Hydroxyurea -- that one is on NLEM and not part of the real shortage story

RNG = np.random.default_rng(20211923)  # seeded on the real Karnataka HC PIL order date (23 Sep 2021)


def load_real_stockout_distribution() -> np.ndarray:
    cag = json.loads(CAG_PATH.read_text(encoding="utf-8"))
    vals = []
    vals.extend(cag["ksmscl_essential_drug_procurement_rate"]["by_year"].values())  # procurement rate -> non-procurement is the shortfall
    vals = [100 - v for v in vals]
    for tier in cag["essential_drug_availability_shortage_by_facility_tier"]["by_tier"].values():
        vals.append(tier["shortage_pct"])
    for d in cag["district_supply_shortfall_pct"]["by_district"].values():
        vals.append(d["shortfall_pct"])
    return np.array(vals, dtype=float) / 100.0


def load_real_procurement_cycle_days() -> np.ndarray:
    """Real KSMSCL committee-meeting-to-purchase-order cycle lengths, in
    days, 2016-17 to 2020-21 (Table 4.2) -- the actual, documented, no-fixed-
    calendar bureaucratic lead time this project models a bulk-restock delay
    on, instead of an invented window."""
    cag = json.loads(CAG_PATH.read_text(encoding="utf-8"))
    return np.array(cag["ksmscl_real_procurement_cycle_timeline"]["real_full_cycle_length_days"], dtype=float)


def drug_category(drug: str) -> str:
    for cat, names in DRUG_BASKET.items():
        if drug in names:
            return cat
    return "other"


def weather_multiplier_array(cat: str, rain_mm: np.ndarray, temp_max_c: np.ndarray) -> np.ndarray:
    """Vectorized real-weather-driven demand multiplier (same rule table as
    the guide's leading-indicator fusion), applied across a whole date range
    at once instead of a per-day Python loop -- this is a performance
    refactor only, the rule values are unchanged."""
    mult = np.ones_like(rain_mm, dtype=float)
    if cat == "envenomation":
        mult *= 1.0 + np.minimum(rain_mm / 15.0, 3.0)
    if cat == "fluids":
        mult *= 1.0 + np.minimum(rain_mm / 25.0, 1.5) + np.maximum(0.0, (temp_max_c - 38) / 10.0)
    if cat == "anti_tb":
        mult *= 1.0 + np.minimum(rain_mm / 60.0, 0.3)
    return mult


def align_weather_to_dates(weather_df: pd.DataFrame, dates: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """Reindex a district's real weather onto the full date range ONCE
    (called per facility, not per facility-drug pair -- weather doesn't
    vary by drug)."""
    w = weather_df.set_index("date").reindex(dates)
    rain = w["rain_mm"].fillna(0.0).to_numpy()
    temp = w["temp_max_c"].fillna(30.0).to_numpy()
    return rain, temp


def sample_stockout_rate(district: str, base_dist: np.ndarray) -> float:
    if district in CAG_TEST_CHECKED_DISTRICT_SHORTFALL_PCT:
        real_rate = CAG_TEST_CHECKED_DISTRICT_SHORTFALL_PCT[district]
        return float(np.clip(RNG.normal(real_rate, 0.05), 0.05, 0.95))
    return float(RNG.choice(base_dist))


def simulate_facility_drug(
    facility_id: str,
    facility_type: str,
    drug: str,
    dates: pd.DatetimeIndex,
    rain_arr: np.ndarray,
    temp_arr: np.ndarray,
    stockout_rate_sample: float,
    procurement_cycle_days: np.ndarray,
) -> pd.DataFrame:
    n = len(dates)
    cat = drug_category(drug)

    size_factor = {
        "District Hospital": 3.2, "General Hospital": 2.4, "Taluk Hospital": 2.0,
        "CHC": 1.5, "PHC": 1.0, "Sub-Centre": 0.5, "Pharmacy/Dispensary": 0.6,
    }.get(facility_type, 1.0)
    base_daily_consumption = size_factor * RNG.uniform(3.0, 9.0)
    target_days_of_cover = RNG.uniform(35, 55)

    if drug in CHRONIC_SHORTAGE_DRUGS:
        return _simulate_chronic_shortage(facility_id, drug, cat, dates, base_daily_consumption)

    wmult = weather_multiplier_array(cat, rain_arr, temp_arr)
    day_idx = np.arange(n)
    weekly_wobble = 1.0 + 0.15 * np.sin(2 * np.pi * day_idx / 7)
    noise = RNG.normal(1.0, 0.08, size=n)
    consumption = np.maximum(0.0, base_daily_consumption * wmult * weekly_wobble * noise)

    stock = np.zeros(n)
    stock[0] = base_daily_consumption * target_days_of_cover

    # Facility-level local stock review is fortnightly (review_interval=14),
    # comfortably inside target_days_of_cover so a healthy facility's normal
    # restock sawtooth never grazes the 14-day critical line on its own --
    # only a real disruption should push it there. The BIG bulk restock a
    # review can trigger, once disrupted, is gated by KSMSCL's real,
    # documented, no-fixed-calendar procurement cycle (357-575 real days,
    # Table 4.2), not an invented window. disruption_prob_per_review is the
    # real CAG stockout-rate sample directly (no artificial amplification).
    # During the real wait, the audit's own finding that "institutions had
    # to locally procure drugs at higher rates" is modeled as smaller,
    # frequent interim trickle restocks -- checked every day, independent of
    # the fortnightly review, so it isn't accidentally starved by interval
    # alignment.
    disruption_prob_per_review = min(0.75, stockout_rate_sample)
    review_interval = 14
    local_purchase_interval = 20
    supply_shortfall_active_until = -1
    in_disruption = False

    for i in range(1, n):
        stock[i] = stock[i - 1] - consumption[i]
        avg_c = consumption[max(0, i - 14): i].mean()

        if i % review_interval == 0:
            days_cover = stock[i] / avg_c if avg_c > 0 else 999
            needs_reorder = days_cover < target_days_of_cover * 0.6
            if needs_reorder and not in_disruption:
                disrupted = RNG.uniform(0, 1) < disruption_prob_per_review
                if disrupted:
                    cycle_days = int(RNG.choice(procurement_cycle_days))
                    supply_shortfall_active_until = i + cycle_days
                    in_disruption = True
            if needs_reorder and not in_disruption:
                stock[i] += avg_c * target_days_of_cover

        if in_disruption and i >= supply_shortfall_active_until:
            stock[i] += avg_c * target_days_of_cover
            in_disruption = False
        elif in_disruption and i % local_purchase_interval == 0:
            # partial, higher-cost local procurement (real audit finding)
            stock[i] += avg_c * target_days_of_cover * 0.4

        stock[i] = max(0.0, stock[i])

    df = pd.DataFrame({
        "date": dates, "facility_id": facility_id, "drug": drug, "drug_category": cat,
        "consumption": consumption, "stock": stock,
    })
    trailing = df["consumption"].rolling(7, min_periods=1).mean()
    df["days_of_cover"] = (df["stock"] / trailing.replace(0, np.nan)).fillna(999).clip(upper=999)
    return df


def _simulate_chronic_shortage(facility_id: str, drug: str, cat: str, dates: pd.DatetimeIndex, nominal_consumption: float) -> pd.DataFrame:
    """Deferoxamine/Deferasirox/Deferiprone: real demand exists (patients need
    it) but real supply has been ~zero since 2020 and remained so through the
    2021 HC PIL and the 2023 failed tenders -- our 2023-2024 window sits
    entirely inside that real persistent-shortage period, so stock stays near
    zero throughout rather than declining-then-recovering."""
    n = len(dates)
    demand = np.maximum(0.0, nominal_consumption * RNG.normal(1.0, 0.1, size=n))
    stock = np.abs(RNG.normal(0.0, nominal_consumption * 0.05, size=n))  # negligible informal/leftover stock, never a real restock
    unmet_demand = demand  # nothing is actually dispensed from the (near-empty) government supply
    df = pd.DataFrame({
        "date": dates, "facility_id": facility_id, "drug": drug, "drug_category": cat,
        "consumption": unmet_demand, "stock": stock,
    })
    trailing = df["consumption"].rolling(7, min_periods=1).mean()
    df["days_of_cover"] = (df["stock"] / trailing.replace(0, np.nan)).fillna(0).clip(upper=999)
    return df


def main():
    facilities = pd.read_csv(FACILITIES_PATH)
    weather = pd.read_csv(WEATHER_PATH, parse_dates=["date"])
    stockout_dist = load_real_stockout_distribution()
    procurement_cycle_days = load_real_procurement_cycle_days()
    print(f"Real CAG Karnataka empirical stockout-rate distribution: n={len(stockout_dist)}, "
          f"mean={stockout_dist.mean():.2%}, range=[{stockout_dist.min():.0%}, {stockout_dist.max():.0%}]")
    print(f"Real KSMSCL procurement cycle length (days): {sorted(procurement_cycle_days.astype(int))}")

    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    weather_by_district = {
        district: align_weather_to_dates(grp[["date", "rain_mm", "temp_max_c"]], dates)
        for district, grp in weather.groupby("district")
    }

    all_frames = []
    n_facilities = len(facilities)
    for fi, (_, fac) in enumerate(facilities.iterrows()):
        rain_arr, temp_arr = weather_by_district[fac["district"]]
        for drug in ALL_DRUGS:
            stockout_sample = sample_stockout_rate(fac["district"], stockout_dist)
            df = simulate_facility_drug(
                fac["facility_id"], fac["facility_type"], drug, dates, rain_arr, temp_arr,
                stockout_sample, procurement_cycle_days,
            )
            df["district"] = fac["district"]
            df["state"] = fac["state"]
            all_frames.append(df)
        if fi % 100 == 0:
            print(f"  {fi}/{n_facilities} facilities simulated ...", flush=True)

    result = pd.concat(all_frames, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUT_PATH, index=False)

    sample_facility_ids = facilities["facility_id"].head(2).tolist()
    result[result["facility_id"].isin(sample_facility_ids)].to_csv(OUT_CSV_SAMPLE, index=False)

    print(f"Wrote {len(result):,} rows ({result['facility_id'].nunique()} facilities x "
          f"{result['drug'].nunique()} drugs x ~{n_days(result)} days) to {OUT_PATH}")


def n_days(df: pd.DataFrame) -> int:
    return (df["date"].max() - df["date"].min()).days + 1


if __name__ == "__main__":
    main()
