"""
Fetch REAL road-network travel times between facilities in the same district
using the public OSRM routing API (router.project-osrm.org) -- a Tier-1 source
per the build guide. These travel times become the edge weights of the
facility graph used by the cascade-diffusion model and the redistribution
matching engine (w_ij ~ 1 / travel_time).

Districts with more facilities than the public OSRM table endpoint's URL
length allows (empirically, requests above ~100 coordinates return 400 Bad
Request -- hit by Mysuru at 155 and Yadgiri at 163 facilities) are split
into chunks of at most MAX_CHUNK facilities; travel times are computed
within each chunk (a real, OSRM-computed sub-clique), not between chunks.
This is a disclosed simplification for large districts, not a made-up
travel time -- every value that IS written is still a real OSRM query
result.
"""
import time
from pathlib import Path

import pandas as pd
import requests

FACILITIES = Path(__file__).resolve().parent.parent / "data" / "processed" / "facilities.csv"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "travel_times.csv"

OSRM_TABLE_URL = "https://router.project-osrm.org/table/v1/driving/{coords}"
MAX_CHUNK = 80


def fetch_matrix(coords: list[tuple[float, float]]) -> list[list[float]]:
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
    url = OSRM_TABLE_URL.format(coords=coord_str)
    resp = requests.get(url, params={"annotations": "duration"}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise RuntimeError(data)
    return data["durations"]  # seconds


def chunk_list(items: list, size: int) -> list[list]:
    return [items[i: i + size] for i in range(0, len(items), size)]


def fetch_district_rows(grp: pd.DataFrame, district: str, state: str) -> list[dict]:
    grp = grp.reset_index(drop=True)
    rows = []
    chunks = [grp] if len(grp) <= MAX_CHUNK else [grp.iloc[idx].reset_index(drop=True) for idx in chunk_list(list(range(len(grp))), MAX_CHUNK)]
    for chunk in chunks:
        coords = list(zip(chunk["lat"], chunk["lon"]))
        durations = fetch_matrix(coords)
        for i, fi in chunk.iterrows():
            for j, fj in chunk.iterrows():
                if i == j:
                    continue
                dur = durations[i][j]
                if dur is None:
                    continue
                rows.append({
                    "facility_id_from": fi["facility_id"], "facility_id_to": fj["facility_id"],
                    "district": district, "state": state, "travel_time_min": round(dur / 60, 2),
                })
        time.sleep(1.5)
    return rows


def main():
    fac = pd.read_csv(FACILITIES)

    existing = pd.read_csv(OUT_PATH) if OUT_PATH.exists() else pd.DataFrame()
    done_districts = set(existing["district"].unique()) if not existing.empty else set()
    if done_districts:
        print(f"Resuming: already have travel times for {len(done_districts)} districts")

    all_rows = existing.to_dict(orient="records") if not existing.empty else []

    for (state, district), grp in fac.groupby(["state", "district"]):
        if district in done_districts:
            print(f"Skipping {district} (already fetched)")
            continue
        print(f"Fetching OSRM travel-time matrix for {district}, {state} ({len(grp)} facilities) ...")
        try:
            rows = fetch_district_rows(grp, district, state)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        print(f"  -> {len(rows)} real pairs")
        all_rows.extend(rows)
        pd.DataFrame(all_rows).to_csv(OUT_PATH, index=False)

    out = pd.DataFrame(all_rows)
    print(f"Wrote {len(out)} real facility-pair travel times to {OUT_PATH}")


if __name__ == "__main__":
    main()
