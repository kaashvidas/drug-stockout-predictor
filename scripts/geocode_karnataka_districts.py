"""
Real geocoding (OSM Nominatim, free, keyless) of Karnataka's 31 district
headquarters towns -- used as centroids for the per-district Overpass
facility queries. District list verified against Wikipedia's
"List of districts of Karnataka" (see docs/DATA_SOURCES.md).
"""
import json
import time
from pathlib import Path

import requests

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "karnataka_district_centroids.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# (district_name, headquarters_town) -- real, per Wikipedia's district list.
DISTRICTS = [
    ("Bagalkote", "Bagalkote"), ("Bengaluru Urban", "Bengaluru"), ("Bengaluru North", "Doddaballapura"),
    ("Bengaluru South", "Ramanagara"), ("Belagavi", "Belagavi"), ("Ballari", "Ballari"),
    ("Bidar", "Bidar"), ("Vijayapura", "Vijayapura"), ("Chamarajanagara", "Chamarajanagara"),
    ("Chikkaballapura", "Chikkaballapur"), ("Chikmagalur", "Chikmagalur"), ("Chitradurga", "Chitradurga"),
    ("Dakshina Kannada", "Mangaluru"), ("Davanagere", "Davanagere"), ("Dharwad", "Dharwad"),
    ("Gadag", "Gadag"), ("Kalaburagi", "Kalaburagi"), ("Hassan", "Hassan"), ("Haveri", "Haveri"),
    ("Kodagu", "Madikeri"), ("Kolar", "Kolar"), ("Koppal", "Koppal"), ("Mandya", "Mandya"),
    ("Mysuru", "Mysuru"), ("Raichur", "Raichur"), ("Shivamogga", "Shivamogga"), ("Tumakuru", "Tumakuru"),
    ("Udupi", "Udupi"), ("Uttara Kannada", "Karwar"), ("Vijayanagara", "Hosapete"), ("Yadgiri", "Yadgiri"),
]

HEADERS = {"User-Agent": "drug-stockout-predictor/1.0 (hackathon research project; contact via repo)"}


def geocode(town: str, state: str = "Karnataka", country: str = "India", retries: int = 3) -> dict | None:
    params = {"q": f"{town}, {state}, {country}", "format": "json", "limit": 1}
    for attempt in range(retries):
        try:
            resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            results = resp.json()
            if results:
                return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"]), "display_name": results[0]["display_name"]}
            return None
        except Exception as e:
            print(f"    retry ({e})")
            time.sleep(5)
    return None


def main():
    out = []
    for district, town in DISTRICTS:
        print(f"Geocoding {district} (HQ: {town}) ...")
        result = geocode(town)
        if result:
            out.append({"district": district, "headquarters": town, "state": "Karnataka", **result})
            print(f"  -> {result['lat']:.4f}, {result['lon']:.4f}")
        else:
            print(f"  FAILED to geocode {town}")
        time.sleep(1.2)  # Nominatim usage policy: max ~1 req/sec

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(out)}/{len(DISTRICTS)} real district centroids to {OUT_PATH}")


if __name__ == "__main__":
    main()
