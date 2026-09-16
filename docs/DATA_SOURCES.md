# Data provenance — what's real, what's generated, and exactly how

This project follows the build guide's own three-tier honesty policy
(see `docs/build_guide.md`, Section 04) and the user's explicit instruction
that every calculation and model must be traceable to real, verified data —
nothing silently invented. This file is the audit trail: for every dataset
used anywhere in the pipeline, it says where it actually came from, whether
it was fetched live in this repo, and — for the one tier that has to be
generated — exactly which real numbers constrain it.

## Tier 1 — Real, fetched live by scripts in `scripts/`, unmodified

| Dataset | Script | Output | Real source |
|---|---|---|---|
| NLEM 2022 drug catalog (453 real medicines, codes, levels of care) | `scripts/parse_nlem.py` | `data/processed/nlem_catalog.json` | CDSCO official PDF, downloaded byte-for-byte: https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadConsumer/nlem2022.pdf |
| Healthcare facility registry (180 real, named, geolocated facilities across 6 real districts) | `scripts/fetch_facilities_osm.py`, `scripts/build_facility_registry.py` | `data/processed/facilities.csv` | OpenStreetMap Overpass API (live query, real hospital/clinic/pharmacy nodes) |
| District daily weather, 2023-01-01 to 2024-12-31 (temp, precipitation, rain) | `scripts/fetch_weather.py` | `data/raw/weather_daily.csv` | Open-Meteo Archive API (real historical observations) |
| 16-day weather forecast per district | `scripts/fetch_weather.py` | `data/raw/weather_forecast_16day.csv` | Open-Meteo Forecast API (live) |
| Real road-network travel times between every facility pair sharing a district | `scripts/fetch_travel_times.py` | `data/processed/travel_times.csv` (5,220 real pairs) | OSRM public routing API (router.project-osrm.org), real road network |
| CAG audit PDFs (source documents, kept for citation) | manual `curl` | `data/raw/cag_health_infra_2024.pdf`, `data/raw/cag_procurement_2022.pdf` | cag.gov.in, official performance audit reports |

Districts chosen deliberately to match the build guide's own cited case
studies plus each state procurement-corporation model it names: **Sarguja
(Chhattisgarh)**, **Pilibhit (Uttar Pradesh)** — the two real 2023-24 TB
stockout sites — plus **Tiruvallur (Tamil Nadu, TNMSC)**, **Ernakulam
(Kerala, KMSCL)**, **Jaipur (Rajasthan, RMSC)**, and **Nagpur (Maharashtra)**
for cross-state cascade diversity.

## Tier 2 — Real, published ground truth used to calibrate and validate

Extracted and verified directly from the downloaded CAG PDF (not paraphrased
from the build guide — independently re-parsed from the source document):

- **Table 4.3** (CAG Odisha public health infrastructure audit, page 81):
  real per-facility stock-out percentages for 9 District/Medical College
  Hospitals across 6 sampled months (2016-2021), ranging 0-68%.
- **CHC stock-out range**: 16-72% of essential drugs unavailable across 13
  test-checked CHCs; one CHC (Kosagumuda) at 2%.
- **Critical-drug stockout duration**: 3-59 critical drugs unavailable for
  3-410 days across audited hospitals, 2018-22.

All saved with page citations in `data/processed/cag_ground_truth.json`.

The build guide additionally cites a national **11-23% availability band**
and **103/272, 39/149 EDL-drugs-missing** figures from a related CAG
compendium report. That specific national summary table was not present in
the single chapter PDF we were able to download and independently re-parse,
so those two figures are carried as **guide-cited, not independently
re-verified by us** — flagged as such in `cag_ground_truth.json` — while the
Odisha per-facility numbers above ARE independently verified against the raw
PDF text in this repo. They are directionally consistent (Odisha's own
facility-level range spans 0-72% stockout).

TB case-study checkpoints (Pilibhit ~1,200 patients incl. 124 MDR-TB; Sarguja
13 days-of-cover; 18 March 2024 Central TB Division admission) are carried
as guide-cited, sourced to IndiaSpend and Scroll.in reporting named in the
guide — these are specific, named, dated, publicly reported facts, not
recomputed by us from a raw dataset.

## Tier 1 sources named in the guide that we could NOT fetch automatically

Documented honestly rather than silently substituted:

- **NPPA medicine sales volumes** (data.gov.in): the dataset exists and is
  real, but data.gov.in's API requires a personally-registered API key (the
  public demo key returns `"Key not authorised"` for this resource — we
  verified this directly). **This is a manual step the user can complete**
  by registering a free key at https://data.gov.in and dropping it into
  `scripts/fetch_nppa.py` (stubbed, not yet run). Until then, no NPPA-derived
  numbers appear anywhere in this codebase.
- **HMIS facility registry** (2.17 lakh+ facilities): published as aggregate
  reports/portal access, not a flat downloadable file. We substituted real,
  live-queried OpenStreetMap facility data for the same real districts,
  documented above — real named, geolocated facilities, not HMIS's own rows.
- **IDSP weekly outbreak bulletins** and **Nikshay TB dashboards**: both are
  JS-rendered government dashboards without a public flat-file export we
  could reach from a script in this session. The leading-indicator fusion
  module (`ml/fusion.py`) currently runs on the rule table alone against
  real weather data; wiring in live IDSP/Nikshay pulls is listed in
  `docs/NEXT_STEPS.md` as a follow-up, not faked in the meantime.

## Tier 3 — The one acknowledged gap: daily per-facility stock counts

No public source in India publishes this. Per the build guide's own
Section 04 and the user's explicit sign-off, `scripts/generate_synthetic_stock.py`
generates it, but is **constrained to pass exactly through the real
checkpoints above**: the national/Odisha stockout percentage bands, the
Sarguja 13-days-of-cover point, and the Pilibhit patient-exposure scale.
Every value the UI derives from this layer is labeled
**"reconstructed — interpolated between verified checkpoints"** in the
frontend itself (see `frontend/src/components/ReconstructedBadge.tsx`) —
never presented as a live feed. See that script's docstring for the exact
constraint equations.

## What this means for model training

- The **drug catalog, facility identities/locations, travel times, and
  weather** feeding every model are 100% real and independently fetched by
  the scripts in this repo — rerun them any time to refresh.
- The **risk-classification labels and backtest targets** are anchored to
  the real CAG Table 4.3 percentages and the real Sarguja/Pilibhit dates —
  the validation section of the guide (Section 11) asks for exactly this:
  a defensible "flagged N weeks before the real, documented response" claim,
  not an invented accuracy number.
- The **daily stock-level time series** that STL/Prophet decompose is the
  one generated layer, and it is never used as if it were itself a ground
  truth measurement — it is training data for demonstrating the pipeline
  mechanics, checkpoint-anchored so its shape is not arbitrary.
