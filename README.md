# Shortage Cascade

Predicting a medicine shortage before it becomes regional — a forecasting,
spillover-cascade, and redistribution-recommendation layer for India's
public health system, sitting on top of existing state procurement systems
rather than replacing them.

Full specification: `docs/build_guide.md`. Data provenance (what's real,
what's checkpoint-constrained, what's deferred): `docs/DATA_SOURCES.md` and
`docs/NEXT_STEPS.md`.

## What's real vs. generated

Every dataset feeding this project is either fetched live from a real
government/open-data source, or — for the one dataset that provably doesn't
exist publicly anywhere (day-by-day per-facility stock counts) — generated
but hard-constrained to pass through real, cited checkpoints: real CAG
Karnataka audit percentages, and the real, dated 2020-onward Karnataka
thalassemia chelation-drug (Desferal) shortage — documented by a 2021
Karnataka High Court PIL and 2023 follow-up reporting. See
`docs/DATA_SOURCES.md` for the full audit trail.

Covers all 31 real districts of Karnataka's government health facility
network (District/Taluk Hospitals, CHCs, PHCs), not a single case-study
district — the thalassemia story is one drug's real, verified pattern
within that statewide dataset, not the whole system.

## Project structure

```
scripts/    real-data fetch/parse scripts (NLEM PDF, OSM facilities, Open-Meteo, OSRM, CAG PDFs) + the Tier-3 synthetic generator
ml/         STL decomposition, Prophet forecasting, risk classifier, cascade diffusion, redistribution matching, trust score
backend/    FastAPI + JWT/RBAC + SQLite, serving the five role-scoped portal views off one data model
frontend/   React + TypeScript + Tailwind + Recharts + Leaflet
data/       raw/ (real downloads) -> processed/ (cleaned real data + calibration checkpoints) -> synthetic/ (checkpoint-constrained generated layer)
docs/       build guide, data sources, next steps
```

## Running it

### 1. Data pipeline (run once, or to refresh)

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

python scripts/parse_nlem.py                     # real NLEM 2022 drug catalog
python scripts/geocode_karnataka_districts.py    # real district HQ coordinates (Nominatim)
python scripts/fetch_karnataka_facilities.py     # real, government-filtered facilities, all 31 districts (OpenStreetMap)
python scripts/build_karnataka_facility_registry.py
python scripts/fetch_weather.py                  # real Open-Meteo history + 16-day forecast
python scripts/fetch_travel_times.py             # real OSRM travel times
python scripts/generate_synthetic_stock.py       # checkpoint-constrained Tier-3 layer
python -m ml.train_all                           # STL + risk classifier + cascade + validation backtest
```

### 2. Backend

```bash
python backend/run.py    # http://localhost:8000, docs at /docs
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173, proxies /api to the backend
```

Log in with any of the seeded demo accounts shown on the login screen
(facility / district / state / vertical-program / national), password
`demo123` for all.
