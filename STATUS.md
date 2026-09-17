# Project status — Shortage Cascade (Karnataka)

**Last updated:** 2026-09-17, ~13:40 IST. This file is a live tracker, not a
one-time report — it gets updated as the build progresses. For setup
instructions see `README.md`; for full data provenance see
`docs/DATA_SOURCES.md`; for known gaps see `docs/NEXT_STEPS.md`.

## What this project is

A prediction + spillover-cascade + redistribution-recommendation layer for
Karnataka's public essential-medicine supply chain — a decision-support tool
that sits on top of KSMSCL / e-Aushadhi, not a replacement for it. Built
from the "Shortage Cascade" hackathon guide, scoped to a full real state
(Karnataka, all 31 districts) rather than a scattered multi-state sample,
anchored to a real, multi-year, legally-documented case study (the
Desferal/thalassemia chelation-drug shortage) instead of a single-crisis
narrative.

## Current status: 🟡 retraining in progress

| Stage | Status | Detail |
|---|---|---|
| Real data foundation | ✅ Done | NLEM 2022 catalog (453 drugs), 1,403 real government facilities across all 31 Karnataka districts (OSM, government-name-filtered), real weather (22,661 daily rows + live 16-day forecasts), real KSMSCL/CAG audit figures (Report No. 08 of 2024), real Karnataka HC PIL + Deccan Herald thalassemia case study |
| Real road-network travel times | ✅ Done | 75,056 real OSRM pairs across all 31 districts (2 largest districts chunked due to public API limits — disclosed in `docs/DATA_SOURCES.md`) |
| Tier-3 synthetic stock generator | ✅ Done, rebuilt | 24 drugs × 1,403 facilities × 731 days = 24.6M rows. Rebuilt to use the REAL KSMSCL procurement-cycle-length distribution (357-575 real days, CAG Table 4.2) instead of an invented delay window, and to model Deferoxamine/Deferasirox/Deferiprone as a chronic near-zero shortage matching the real 2020-onward timeline |
| ML pipeline retraining | 🟡 **In progress** | Feature build (STL decomposition across ~700k snapshots) completed 14:46 IST. Now training the gradient-boosted risk classifier → cascade stress propagation → validation backtest. This section will be filled in with real numbers the moment it finishes — nothing below is filled in speculatively. |
| Backend restart on new data | ⬜ Not started | Waiting on training to finish |
| Frontend feature verification | 🟡 Partially done | New features (below) are coded and type-checked, but not yet exercised against the live Karnataka dataset |

## Model performance (filled in once training completes — not yet available)

*Nothing in this section is filled in until the actual run finishes and I've
looked at the real numbers. If you're reading a version of this file where
this still says that, training hasn't completed yet.*

- Risk classifier AUC: —
- Precision / recall / F1: —
- Feature importances: —
- Validation backtest result (Karnataka thalassemia chelation-drug shortage,
  persistent-flag claim): —

## Features built this session (coded, pending live-data verification)

- **Search bar** across drugs/facilities/districts (`SearchBar.tsx`)
- **Ranked bar charts** — most at-risk drugs, most at-risk facilities, for
  the national/state/program task-force view (`RankedBarChart.tsx`, backend
  `/api/alerts/rankings/by-drug` and `/by-facility`)
- **Availability Explorer** — look up any drug's availability across every
  facility in scope, or ranked by real travel time from a chosen facility
  (`AvailabilityExplorer.tsx`, backend `/api/alerts/availability/{drug}`)
- **Facility-initiated transfer requests** — a pharmacist can flag stock as
  critical/surplus and request supply from a nearby facility; district/
  state/national roles see and resolve a pending queue
  (`TransferRequest` table, `/api/redistribution/requests*`,
  `PendingTransferRequests.tsx`)
- **Real-weather-aware redistribution routing** — donor routes are derated
  when real same-day rain at the donor's district is heavy, surfaced as a
  "weather risk" badge (`ml/matching.py`, `RedistributionQueue.tsx`)
- **Facility stock-history visualization** — a pharmacist's own submitted
  reports, charted over time (`MyStockHistory.tsx`)
- **Real KSMSCL procurement-cadence-grounded generator** (see above)

## What's next

1. Finish current ML retraining run; fill in the model-performance section
   above with real numbers.
2. Restart the backend against the retrained artifacts; smoke-test every
   endpoint against the real 1,403-facility Karnataka dataset.
3. Exercise the new frontend features (availability explorer, transfer
   requests, weather-flagged routing, stock history) against live data —
   not just type-checked, actually clicked through.
4. Report back with a real accuracy/validation summary, not a placeholder.
