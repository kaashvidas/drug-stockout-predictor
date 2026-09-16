# Shortage Cascade — Build Guide (reference copy)

Source: hackathon build-guide artifact provided by the project owner
(theme: Butterfly Effect / Decent Health & Well-Being). Full original at
the artifact URL shared in project setup. This file condenses it to the
decisions that drive this codebase's structure; see `docs/DATA_SOURCES.md`
for the data-provenance detail and `docs/NEXT_STEPS.md` for what's deferred.

## Purpose
Forecast medicine stockouts before they become regional, model how a
shortage cascades between facilities via shared catchments, and recommend
feasible redistribution — sitting on top of existing state procurement
systems (TNMSC/KMSCL/RMSC, eVIN), not replacing them.

## Seven pipeline modules
1. **Forecasting & decomposition** — STL splits each facility-drug
   consumption series into trend/seasonal/residual; a declining trend slope
   is a structural risk, a dip confined to seasonal/residual is temporary.
2. **Leading-indicator fusion** — IDSP outbreak categories + Open-Meteo
   thresholds adjust a forward demand multiplier per drug category ahead of
   consumption data moving.
3. **Spillover-cascade model** — facilities are graph nodes; edges weighted
   by inverse OSRM travel time; stress diffuses with decay:
   `stress_i(t+1) = own_stress_i + δ·Σⱼ w_ij·stress_j(t)`, `w_ij ∝ 1/travel_time(i,j)`.
4. **Redistribution/matching engine** — ranks donor→recipient candidates:
   `score = w1·urgency + w2·(1/travel_time) + w3·(1/days_to_expiry) − w4·donor_shortfall_risk`.
   Recommend-only, human approves every transfer.
5. **Reporting-trust layer** — `trust_i = 0.5·(reports_received/expected, trailing 8wk) + 0.5·(1−revision_volatility)`,
   shown as a confidence band on every alert.
6. Role-based unified portal (five views, one data model — see below).
7. Audit trail — every alert and approved transfer logged once, visible
   (scoped) at every level above it.

## Five portal views, one backend
Facility (PHC/CHC pharmacists) → District (program managers) → State
(procurement corporations) → Vertical programs (Central TB Division,
NVBDCP, Immunization Division) → National (ministry/task force). RBAC scopes
the same API and data model per role; no separate apps.

## Stack (as specified)
Python/pandas for wrangling; FastAPI + SQLite backend; statsmodels (STL) +
Prophet for forecasting; scikit-learn for interpretable risk classification;
NetworkX for the cascade graph; OSRM for routing; React + TypeScript +
Tailwind + Recharts + Leaflet for the frontend; JWT-based RBAC.

## Validation approach (Section 11)
No invented accuracy percentage. Backtest against real Tier-2 checkpoints:
hide the final weeks of the reconstructed Sarguja/Pilibhit trajectory, run
the pipeline, and confirm the structural-decline classifier would have
flagged it before the real 18 March 2024 Central TB Division admission date.

## Data tiering (Section 04) — see docs/DATA_SOURCES.md for what this repo actually did
- **Tier 1**: real, pull as-is (NLEM, HMIS, IDSP, Nikshay, NPPA, NFHS-5,
  Open-Meteo, OSM/OSRM).
- **Tier 2**: real, published ground truth used as calibration/validation
  targets (CAG audits, Punjab/Haryana availability study, 2023-24 TB
  stockout reporting, 2021 oxygen crisis court record).
- **Tier 3**: the one acknowledged gap — no public live per-facility daily
  stock feed exists in India. Generate it, but constrain the generator to
  pass exactly through the real Tier-2 checkpoints; label every
  guide-derived chart in the UI as reconstructed/interpolated.
