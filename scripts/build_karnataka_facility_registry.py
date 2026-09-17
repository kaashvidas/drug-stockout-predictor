"""
Clean the government-filtered Karnataka OSM facility pull into the working
facility registry. No per-district cap -- real government facility density
varies genuinely by district (a dense district like Bengaluru Urban
legitimately has more government hospitals than a small rural district),
and the government-name filter already keeps the total tractable (~1,000
statewide, not the tens of thousands an unfiltered pull would return).

Input:  data/raw/karnataka_osm_facilities.json  (real, government-filtered)
Output: data/processed/facilities.csv           (replaces the prior 6-district version)
"""
import json
import re
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "karnataka_osm_facilities.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "facilities.csv"

TYPE_PATTERNS = [
    (re.compile(r"district hospital", re.I), "District Hospital"),
    (re.compile(r"taluk hospital", re.I), "Taluk Hospital"),
    (re.compile(r"community health cent|\bchc\b", re.I), "CHC"),
    (re.compile(r"primary health cent|\bphc\b", re.I), "PHC"),
    (re.compile(r"general hospital|civil hospital|state hospital|corporation hospital", re.I), "General Hospital"),
    (re.compile(r"sub[- ]?cent", re.I), "Sub-Centre"),
]


def classify_type(name: str, amenity: str) -> str:
    for pattern, label in TYPE_PATTERNS:
        if pattern.search(name):
            return label
    if amenity == "pharmacy":
        return "Pharmacy/Dispensary"
    if amenity == "hospital":
        return "General Hospital"
    return "PHC"


def main():
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(raw)
    df = df.drop_duplicates(subset=["name", "district", "lat", "lon"])
    df["facility_type"] = [classify_type(n, a) for n, a in zip(df["name"], df["amenity"])]

    df = df.sort_values(["state", "district"]).reset_index(drop=True)
    df["facility_id"] = [f"FAC{i+1:04d}" for i in range(len(df))]

    out = df[["facility_id", "name", "facility_type", "district", "state", "lat", "lon", "osm_id"]].rename(
        columns={"name": "facility_name"}
    )
    out["source"] = "OpenStreetMap Overpass API, government-facility-filtered (real, live-fetched)"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"Wrote {len(out)} real Karnataka government facilities to {OUT_PATH}")
    print(out.groupby("district").size().sort_values(ascending=False))
    print(out["facility_type"].value_counts())


if __name__ == "__main__":
    main()
