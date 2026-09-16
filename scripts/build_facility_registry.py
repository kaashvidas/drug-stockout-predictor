"""
Clean the raw OSM facility pull into the working facility registry used by the
rest of the pipeline. Caps each district to a hackathon-manageable count while
preferring real hospitals/clinics (public-health-relevant) over generic
pharmacies, and de-duplicates near-identical entries.

Input:  data/raw/osm_facilities.json   (real, from Overpass API)
Output: data/processed/facilities.csv  (real names/coords, derived facility_id)
"""
import json
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "osm_facilities.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "facilities.csv"

MAX_PER_DISTRICT = 30

AMENITY_TO_TYPE = {
    "hospital": "District Hospital",
    "clinic": "CHC",
    "pharmacy": "Pharmacy/Dispensary",
    "centre": "PHC",
    "doctor": "PHC",
}

TYPE_PRIORITY = {"District Hospital": 0, "CHC": 1, "PHC": 2, "Pharmacy/Dispensary": 3}


def main():
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(raw)
    df = df.drop_duplicates(subset=["name", "district"])
    df["facility_type"] = df["amenity"].map(AMENITY_TO_TYPE).fillna("PHC")
    df["priority"] = df["facility_type"].map(TYPE_PRIORITY).fillna(9)

    kept = []
    for (district, state), grp in df.groupby(["district", "state"]):
        grp_sorted = grp.sort_values("priority")
        kept.append(grp_sorted.head(MAX_PER_DISTRICT))
    result = pd.concat(kept, ignore_index=True)

    result = result.sort_values(["state", "district", "priority"]).reset_index(drop=True)
    result["facility_id"] = [f"FAC{i+1:04d}" for i in range(len(result))]

    out = result[[
        "facility_id", "name", "facility_type", "district", "state", "lat", "lon", "osm_id",
    ]].rename(columns={"name": "facility_name"})
    out["source"] = "OpenStreetMap Overpass API (real, live-fetched)"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"Wrote {len(out)} facilities to {OUT_PATH}")
    print(out.groupby(["state", "district"]).size())
    print(out["facility_type"].value_counts())


if __name__ == "__main__":
    main()
