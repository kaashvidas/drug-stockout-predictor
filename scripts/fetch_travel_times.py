"""
Fetch REAL road-network travel times between facilities in the same district
using the public OSRM routing API (router.project-osrm.org) -- a Tier-1 source
per the build guide. These travel times become the edge weights of the
facility graph used by the cascade-diffusion model and the redistribution
matching engine (w_ij ~ 1 / travel_time).
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

FACILITIES = Path(__file__).resolve().parent.parent / "data" / "processed" / "facilities.csv"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "travel_times.csv"

OSRM_TABLE_URL = "https://router.project-osrm.org/table/v1/driving/{coords}"


def fetch_matrix(coords: list[tuple[float, float]]) -> list[list[float]]:
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
    url = OSRM_TABLE_URL.format(coords=coord_str)
    resp = requests.get(url, params={"annotations": "duration"}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise RuntimeError(data)
    return data["durations"]  # seconds


def main():
    fac = pd.read_csv(FACILITIES)
    rows = []

    for (state, district), grp in fac.groupby(["state", "district"]):
        grp = grp.reset_index(drop=True)
        coords = list(zip(grp["lat"], grp["lon"]))
        print(f"Fetching OSRM travel-time matrix for {district}, {state} ({len(coords)} facilities) ...")
        try:
            durations = fetch_matrix(coords)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        for i, fi in grp.iterrows():
            for j, fj in grp.iterrows():
                if i == j:
                    continue
                dur = durations[i][j]
                if dur is None:
                    continue
                rows.append(
                    {
                        "facility_id_from": fi["facility_id"],
                        "facility_id_to": fj["facility_id"],
                        "district": district,
                        "state": state,
                        "travel_time_min": round(dur / 60, 2),
                    }
                )
        time.sleep(1.5)

    out = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} real facility-pair travel times to {OUT_PATH}")


if __name__ == "__main__":
    main()
