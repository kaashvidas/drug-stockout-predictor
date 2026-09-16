"""
Fetch REAL public healthcare facility locations from OpenStreetMap (Overpass API)
for a curated set of real Indian districts.

Why OSM instead of HMIS microdata directly: HMIS facility registry (2.17 lakh+
facilities) is published as aggregate reports / requires portal access, not a
single flat downloadable file. OSM's Overpass API is a free, keyless, live
government-adjacent-quality source of real, named, geolocated healthcare
facilities (hospitals, clinics, pharmacies) and is what the build guide lists
as a Tier-1 source in its own right (Overpass API, for the routing/road-network
layer) -- we reuse the same real source for facility geolocation too, since it
returns actual named PHCs/CHCs/hospitals with real coordinates, not invented ones.

Districts chosen to match the build guide's real, cited case studies:
  - Sarguja, Chhattisgarh   (2023-24 TB stockout: 13 days-of-cover, CAG-adjacent)
  - Pilibhit, Uttar Pradesh (2023-24 TB stockout: ~1,200 patients incl. 124 MDR-TB)
Plus districts representing each cited state procurement-corporation model:
  - Tiruvallur, Tamil Nadu  (TNMSC)
  - Ernakulam, Kerala       (KMSCL)
  - Jaipur, Rajasthan       (RMSC)
  - Nagpur, Maharashtra     (cross-state diversity for cascade demo)
"""
import json
import time
from pathlib import Path

import requests

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "osm_facilities.json"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Real district centroids (lat, lon) -- publicly known geographic coordinates.
DISTRICTS = [
    {"district": "Sarguja", "state": "Chhattisgarh", "lat": 23.1017, "lon": 83.1965, "radius_m": 30000},
    {"district": "Pilibhit", "state": "Uttar Pradesh", "lat": 28.6314, "lon": 79.8033, "radius_m": 25000},
    {"district": "Tiruvallur", "state": "Tamil Nadu", "lat": 13.1439, "lon": 79.9080, "radius_m": 25000},
    {"district": "Ernakulam", "state": "Kerala", "lat": 9.9816, "lon": 76.2999, "radius_m": 25000},
    {"district": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lon": 75.7873, "radius_m": 30000},
    {"district": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882, "radius_m": 30000},
]

QUERY_TMPL = """
[out:json][timeout:60];
(
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  node["amenity"="clinic"](around:{radius},{lat},{lon});
  node["amenity"="pharmacy"](around:{radius},{lat},{lon});
  node["healthcare"](around:{radius},{lat},{lon});
);
out body;
"""


def fetch_district(d: dict, retries: int = 4) -> list[dict]:
    q = QUERY_TMPL.format(radius=d["radius_m"], lat=d["lat"], lon=d["lon"])
    headers = {
        "User-Agent": "drug-stockout-predictor/1.0 (hackathon research project)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*",
    }
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(OVERPASS_URL, data={"data": q}, headers=headers, timeout=120)
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            break
        except Exception as e:
            last_err = e
            wait = 15 * (attempt + 1)
            print(f"  attempt {attempt + 1} failed ({e}), retrying in {wait}s ...")
            time.sleep(wait)
    else:
        raise last_err
    out = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        out.append(
            {
                "osm_id": el["id"],
                "name": name,
                "lat": el["lat"],
                "lon": el["lon"],
                "amenity": tags.get("amenity") or tags.get("healthcare"),
                "operator_type": tags.get("operator:type") or tags.get("operator"),
                "district": d["district"],
                "state": d["state"],
            }
        )
    return out


def main():
    existing = []
    done_districts = set()
    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        done_districts = {e["district"] for e in existing}
        print(f"Resuming: already have {len(existing)} facilities for {done_districts}")

    all_facilities = list(existing)
    for d in DISTRICTS:
        if d["district"] in done_districts:
            print(f"Skipping {d['district']} (already fetched)")
            continue
        print(f"Querying Overpass for {d['district']}, {d['state']} ...")
        try:
            facs = fetch_district(d)
        except Exception as e:
            print(f"  FAILED after retries: {e}")
            facs = []
        print(f"  -> {len(facs)} real named facilities found")
        all_facilities.extend(facs)
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_facilities, f, indent=2, ensure_ascii=False)
        time.sleep(5)  # be polite to the free public Overpass instance

    print(f"\nWrote {len(all_facilities)} total real facilities to {OUT_PATH}")


if __name__ == "__main__":
    main()
