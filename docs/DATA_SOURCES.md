# Data provenance — what's real, what's generated, and exactly how

This project follows the build guide's own three-tier honesty policy
(see `docs/build_guide.md`, Section 04) and the user's explicit instruction
that every calculation and model must be traceable to real, verified data —
nothing silently invented. This file is the audit trail: for every dataset
used anywhere in the pipeline, it says where it actually came from, whether
it was fetched live in this repo, and — for the one tier that has to be
generated — exactly which real numbers constrain it.

**Scope note:** the platform originally covered 180 facilities scattered
across 6 districts in 6 different states, anchored to a Chhattisgarh/UP TB
stockout case study. It was rebuilt to cover **all 31 real districts of a
single state (Karnataka)**, anchored to a different real, verified case
study (a persistent thalassemia chelation-drug shortage) — both so the
dataset reads as one coherent state health system rather than a scattered
sample, and so the flagship case study isn't the only story the system can
tell (see the "Scope note" in `README.md`).

## Tier 1 — Real, fetched live by scripts in `scripts/`, unmodified

| Dataset | Script | Output | Real source |
|---|---|---|---|
| NLEM 2022 drug catalog (453 real medicines, codes, levels of care) | `scripts/parse_nlem.py` | `data/processed/nlem_catalog.json` | CDSCO official PDF, downloaded byte-for-byte: https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadConsumer/nlem2022.pdf |
| Karnataka's 31 real district HQ coordinates | `scripts/geocode_karnataka_districts.py` | `data/raw/karnataka_district_centroids.json` | OSM Nominatim (live geocoding, free, keyless) |
| Government-facility registry, statewide (all 31 districts) | `scripts/fetch_karnataka_facilities.py`, `scripts/build_karnataka_facility_registry.py` | `data/processed/facilities.csv` | OpenStreetMap Overpass API (live query, government-name-filtered — see note below) |
| District daily weather, 2023-01-01 to 2024-12-31 (temp, precipitation, rain) | `scripts/fetch_weather.py` | `data/raw/weather_daily.csv` | Open-Meteo Archive API (real historical observations) |
| 16-day weather forecast per district | `scripts/fetch_weather.py` | `data/raw/weather_forecast_16day.csv` | Open-Meteo Forecast API (live) |
| Real road-network travel times between every facility pair sharing a district | `scripts/fetch_travel_times.py` | `data/processed/travel_times.csv` | OSRM public routing API (router.project-osrm.org), real road network |
| CAG Karnataka audit PDF (source document, kept for citation) | manual `curl` | `data/raw/cag_karnataka_2024.pdf` | cag.gov.in, Report No. 08 of 2024, Government of Karnataka |

**The government-facility filter, and why it exists:** an early, unfiltered
Overpass pull for Bengaluru Urban district alone returned 3,144 "healthcare"
nodes — 97% of them private clinics, pharmacies, dentists, and diagnostic
labs, not the government District/Taluk Hospital, CHC, and PHC network that
KSMSCL supplies and the CAG audit examines. `scripts/fetch_karnataka_facilities.py`
filters to facilities that are either OSM-tagged `operator:type=government`
or name-pattern-matched as government (`"Government Hospital"`, `"PHC"`,
`"Taluk Hospital"`, `"CHC"`, etc. — India's public facilities reliably
self-identify by name). This cut Bengaluru Urban to 63 real government
facilities and kept the final statewide total at 1,403 real facilities
across all 31 districts instead of tens of thousands, while making the
dataset actually representative of the public essential-drug supply chain
this whole platform models. (672 PHCs, 482 general hospitals, 157
sub-centres, 74 CHCs, 10 district hospitals, 7 taluk hospitals, 1 pharmacy
-- see `data/processed/facilities.csv`.) Real road-network travel times
were computed for all 75,056 same-district facility pairs
(`data/processed/travel_times.csv`); the two largest districts (Mysuru,
155 facilities; Yadgiri, 163) exceeded the public OSRM table endpoint's
per-request coordinate limit and were split into real, OSRM-computed
sub-clique chunks of ≤80 facilities rather than one full clique -- a
disclosed simplification, not a fabricated travel time (see
`scripts/fetch_travel_times.py`).

## Tier 2 — Real, published ground truth used to calibrate and validate

Extracted and independently verified directly from the downloaded, real
Karnataka-specific CAG PDF (**Report No. 08 of 2024, Government of
Karnataka, on Public Health Infrastructure and Management of Health
Services**, https://cag.gov.in/uploads/download_audit_report/2024/Report-No.-8,-2024,-Karnataka-06a2bce5ec213d0.88550062.pdf
— 208 pages, downloaded and re-parsed in this repo, not paraphrased from a
secondary article):

- **Table 4.3** (page 82): KSMSCL's own year-wise essential-drug
  procurement rate — 66.89% (2017-18), 40.52% (2018-19), 43.53% (2019-20),
  31.27% (2020-21).
- **Table 4.5** (page 83): real supply-vs-requisition percentages in the
  audit's own 5 test-checked districts — Ballari 34.65%, Bengaluru Urban
  32.95%, Dharwad 32.10%, Kolar 33.07%, Mysuru 30.84%.
- **Essential-drug availability by facility tier** (page 85, snapshot date
  30 June 2022): District Hospitals had fewer than 50 of 128 required
  drugs (61% shortage); Taluk Hospitals ≤35 of 81 (57%); CHCs ≤25 of 64
  (61%).
- **OPD patient survey** (page 85, n=1,260): only 70% (tertiary), 91%
  (secondary), 92% (primary) of outpatients actually received their
  prescribed drug at the counter.
- **Table 4.2** (page 82): the real, dated timeline of KSMSCL's own annual
  procurement cycle (State Therapeutic Committee meeting → indent
  submission → Need Assessment Committee meeting → government approval →
  tender → purchase order) for 2016-17 through 2021-22 -- the audit's own
  finding is that **no fixed calendar schedule existed** for this cycle,
  so real committee-meeting-to-purchase-order lengths vary from 357 to 575
  days. This real range is used directly (not invented) as the
  distribution for how long a procurement disruption realistically lasts
  once triggered in the generator (`scripts/generate_synthetic_stock.py`),
  replacing an earlier, made-up 15-45 day placeholder.

All saved with page citations in `data/processed/cag_karnataka_ground_truth.json`.

**A correction worth recording:** the first CAG PDF fetched for this
project's Karnataka pivot was actually Andhra Pradesh's, not Karnataka's —
both reports share the generic filename pattern `Chapter-IV---Availability-of-Drugs...`.
That file is kept at `data/raw/cag_andhra_pradesh_2024_MISLABELED.pdf` as a
record of the mistake and is not used anywhere in this pipeline; the real
Karnataka-specific report (Report No. 08 of 2024) was located and verified
separately.

**The flagship case study — a real, multi-year, legally-documented
persistent shortage** (not the single-admission-date crisis pattern the
project used previously):

- **Since 2020**: Desferal (Deferoxamine), the standard thalassemia
  iron-chelation injection, disappeared from Karnataka government hospital
  shelves, per both sources below.
- **23 September 2021**: the Karnataka High Court ordered notice to the
  state government on a PIL filed by the **Thalassemia and Sickle Cell
  Society of Bangalore** and patient **Namitha A Kumar**, seeking restored
  free supply. Real petitioners, real bench (Acting Chief Justice Satish
  Chandra Sharma), real cited figure of ~17,000 affected patients
  statewide. Source: Deccan Herald, https://www.deccanherald.com/india/karnataka/plea-in-karnataka-hc-seeks-regular-supply-of-life-saving-drug-for-thalassemia-patients-1033539.html
- **2 October 2023**: follow-up reporting confirms the drug is still
  missing; KSMSCL's own procurement tender drew no bidders, twice. Source:
  Deccan Herald, https://www.deccanherald.com/india/karnataka/bengaluru/lack-of-vital-drug-in-karnatakas-govt-hospitals-hits-thalassemia-patients-2708716

Full timeline with every figure in `data/processed/cag_karnataka_ground_truth.json`.

## Tier 1 sources named in the guide that we could NOT fetch automatically

Documented honestly rather than silently substituted:

- **NPPA medicine sales volumes** (data.gov.in): the dataset exists and is
  real, but data.gov.in's API requires a personally-registered API key (the
  public demo key returns `"Key not authorised"` for this resource — we
  verified this directly). **This is a manual step the user can complete**
  by registering a free key at https://data.gov.in. Until then, no
  NPPA-derived numbers appear anywhere in this codebase.
- **HMIS facility registry** (2.17 lakh+ facilities): published as aggregate
  reports/portal access, not a flat downloadable file. We substituted real,
  live-queried, government-filtered OpenStreetMap facility data for all 31
  Karnataka districts, documented above — real named, geolocated
  facilities, not HMIS's own rows.
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
checkpoints above**:

- Each facility-drug pair's long-run stockout-rate parameter is sampled
  from the empirical distribution of the real Karnataka CAG percentages
  above — facilities in the audit's own 5 test-checked districts are
  biased toward THAT district's own real reported shortfall rate rather
  than a statewide average.
- **Deferoxamine, Deferasirox, and Deferiprone** (the three real
  iron-chelation drugs named across the court/news sources — none of them
  on the NLEM 2022 list, which is itself part of the real story) are
  hard-constrained to near-zero stock for the entire 2023-2024 window,
  reflecting the real, dated, persistent (not resolved-crisis) shortage.
  **Hydroxyurea**, a fourth real thalassemia-adjacent drug that IS on
  NLEM 2022, is deliberately NOT forced into the shortage pattern — it
  follows the general stochastic model like every other basket drug.

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
  the real Karnataka CAG percentages and the real HC PIL / Deccan Herald
  dates — the validation section of the guide (Section 11) asks for
  exactly this: a defensible claim tied to real dates, not an invented
  accuracy number. Because this case study is a *persistent* shortage
  rather than a single-admission-date crisis, the corresponding backtest
  (`ml/train_all.py::run_validation_backtest`) checks that the model
  flags it as critical *consistently*, not just *early* — a different
  but equally real shape of claim.
- The **daily stock-level time series** that STL/Prophet decompose is the
  one generated layer, and it is never used as if it were itself a ground
  truth measurement — it is training data for demonstrating the pipeline
  mechanics, checkpoint-anchored so its shape is not arbitrary.
