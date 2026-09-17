"""
Fetch REAL healthcare facility locations from OpenStreetMap (Overpass API)
for every one of Karnataka's 31 real districts -- full statewide coverage,
no per-district cap (per project owner's explicit choice). Supersedes the
earlier 6-district multi-state scripts/fetch_facilities_osm.py.

Radius per district approximates its administrative area from its real,
geocoded headquarters centroid (see scripts/geocode_karnataka_districts.py)
-- a simplification (a circle isn't a district boundary), same one already
used for the original 6-district dataset, noted here rather than hidden.
"""
import json
import re
import time
from pathlib import Path

import requests

# Government/public facility filter. India's public health facilities are
# reliably self-identified by name in OSM ("Government Hospital", "PHC",
# "Taluk Hospital", etc.) -- this is the real signature of the KSMSCL/CAG
# subject matter this whole platform models, unlike the thousands of
# private clinics/pharmacies/dental practices OSM also returns per query
# (verified: an early unfiltered pull of Bengaluru Urban alone returned
# 3,144 healthcare nodes, 97% private clinics/pharmacies/dentists/labs --
# see docs/DATA_SOURCES.md for the full note). Filtering to this pattern
# is what keeps the dataset representative of the actual public system.
GOVERNMENT_NAME_PATTERN = re.compile(
    r"government|govt\.?|district hospital|taluk hospital|primary health cent|"
    r"community health cent|\bphc\b|\bchc\b|general hospital|civil hospital|"
    r"sub[- ]?cent(?:re|er)|\besi\b|municipal|corporation hospital|state hospital",
    re.IGNORECASE,
)

CENTROIDS_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "karnataka_district_centroids.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "karnataka_osm_facilities.json"

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Larger districts (by real land area) get a larger search radius; Bengaluru
# Urban is deliberately smaller since it's a dense city district.
LARGE_DISTRICTS = {"Uttara Kannada", "Belagavi", "Bidar", "Kalaburagi", "Raichur", "Chitradurga", "Tumakuru", "Mysuru", "Ballari", "Dharwad", "Koppal", "Yadgiri", "Vijayapura", "Chikmagalur"}
SMALL_DISTRICTS = {"Bengaluru Urban", "Bengaluru North", "Bengaluru South", "Kodagu"}

QUERY_TMPL = """
[out:json][timeout:180];
(
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  node["amenity"="clinic"](around:{radius},{lat},{lon});
  node["amenity"="pharmacy"](around:{radius},{lat},{lon});
  node["healthcare"](around:{radius},{lat},{lon});
);
out body;
"""


def radius_for(district: str) -> int:
    if district in LARGE_DISTRICTS:
        return 40000
    if district in SMALL_DISTRICTS:
        return 20000
    return 30000


def fetch_district(centroid: dict, retries: int = 4) -> list[dict]:
    radius = radius_for(centroid["district"])
    q = QUERY_TMPL.format(radius=radius, lat=centroid["lat"], lon=centroid["lon"])
    headers = {"User-Agent": "drug-stockout-predictor/1.0 (hackathon research project)"}

    last_err = None
    for attempt in range(retries):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            resp = requests.post(url, data={"data": q}, headers=headers, timeout=200)
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            break
        except Exception as e:
            last_err = e
            wait = 15 * (attempt + 1)
            print(f"    attempt {attempt + 1} via {url} failed ({e}), retrying in {wait}s ...")
            time.sleep(wait)
    else:
        raise last_err

    out = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        operator_type = (tags.get("operator:type") or "").lower()
        is_gov_tagged = operator_type in ("government", "public")
        is_gov_named = bool(GOVERNMENT_NAME_PATTERN.search(name))
        if not (is_gov_tagged or is_gov_named):
            continue
        out.append(
            {
                "osm_id": el["id"],
                "name": name,
                "lat": el["lat"],
                "lon": el["lon"],
                "amenity": tags.get("amenity") or tags.get("healthcare"),
                "operator": tags.get("operator"),
                "operator_type": tags.get("operator:type"),
                "district": centroid["district"],
                "state": "Karnataka",
            }
        )
    return out


def main():
    centroids = json.loads(CENTROIDS_PATH.read_text(encoding="utf-8"))

    existing = []
    done_districts = set()
    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        done_districts = {e["district"] for e in existing}
        print(f"Resuming: already have {len(existing)} facilities across {len(done_districts)} districts")

    all_facilities = list(existing)
    for c in centroids:
        if c["district"] in done_districts:
            print(f"Skipping {c['district']} (already fetched)")
            continue
        print(f"Querying Overpass for {c['district']} (radius {radius_for(c['district'])/1000:.0f}km) ...")
        try:
            facs = fetch_district(c)
        except Exception as e:
            print(f"  FAILED after retries: {e}")
            facs = []
        print(f"  -> {len(facs)} real named facilities found")
        all_facilities.extend(facs)
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_facilities, f, indent=2, ensure_ascii=False)
        time.sleep(4)

    print(f"\nTotal: {len(all_facilities)} real Karnataka facilities across {len(centroids)} districts")
    by_district = {}
    for f in all_facilities:
        by_district[f["district"]] = by_district.get(f["district"], 0) + 1
    for d, n in sorted(by_district.items(), key=lambda x: -x[1]):
        print(f"  {d}: {n}")


if __name__ == "__main__":
    main()
