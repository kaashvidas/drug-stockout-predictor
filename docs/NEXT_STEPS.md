# Next steps / known follow-ups

Things deliberately deferred rather than faked. See docs/DATA_SOURCES.md for
the full data-provenance detail behind each item.

## Data

- **e-Aushadhi / e-Aushada (KSMSCL's real procurement software)**: the
  Karnataka CAG audit itself names this as the real system KSMSCL already
  uses to manage procurement/distribution and to record per-institution
  drug availability (cited directly in the report we downloaded and
  parsed, page 109/111). This is the real integration point named in the
  build guide's own Tier-3 roadmap ("a data-sharing integration with each
  state's own procurement/e-tracking system... under an MoU"). Connecting
  to it would replace `scripts/generate_synthetic_stock.py`'s output
  entirely with real daily stock data for the facilities it covers — the
  single highest-value next step for this project, and the reason every
  other piece (facility identities, drug catalog, RBAC, matching engine)
  was built to be data-source-agnostic rather than hard-coded around the
  synthetic layer. In the meantime, all daily stock/consumption values
  remain the one clearly-labeled generated layer; nothing about KSMSCL's
  real systems is fabricated to look otherwise.
- **NPPA sales volumes**: register a free API key at https://data.gov.in and
  wire it into a new `scripts/fetch_nppa.py`; currently no NPPA-derived
  number appears anywhere in this codebase.
- **IDSP weekly outbreak bulletins**: JS-rendered without a reachable
  flat-file export we could find in this session. `ml/fusion.py` already
  accepts an `idsp_signal` parameter and has the rule table wired — it just
  isn't fed live data yet. `scripts/fetch_travel_times.py` and
  `scripts/fetch_weather.py` are the pattern to follow once a real endpoint
  is found (or an official CSV export becomes available). This is the one
  piece of "forecast based on local disease outbreak news" not yet wired to
  a real feed — the weather half of that forecast IS real and live (see
  `ml/forecasting.py`).
- **HMIS's own facility registry**: substituted with real,
  government-filtered OpenStreetMap facility data for all 31 real Karnataka
  districts (documented, not hidden). A real deployment would integrate
  the actual HMIS registry via the same kind of MoU the build guide
  describes for Tier 3.

## Modeling

- The risk classifier's dominant feature is `current_days_of_cover`
  (importance ~0.995) rather than the STL trend slope -- meaning the
  "structural vs. temporary" distinction is currently surfaced as its own
  explicit boolean (`is_structural_decline`, from `ml/decomposition.py`'s
  slope threshold) alongside the ML probability, not fused into a single
  blended score. A richer label design would let trend_slope carry more
  weight in the classifier itself.
- Cascade stress propagation is computed from a single current-state
  snapshot (3 diffusion iterations), not simulated day-by-day across the
  full 2-year history. A historical cascade backtest (did neighboring
  facilities' risk visibly rise before their own data showed decline?)
  would strengthen the "predicts spillover" claim with a concrete number.
- The Section-11 validation backtest now covers the Karnataka thalassemia
  chelation-drug shortage (persistent-flag shape, not single-admission-date
  shape -- see `ml/train_all.py::run_validation_backtest`). It has not yet
  been extended to a second, independent real checkpoint for
  cross-validation.

## Backend / frontend

- Redistribution donor pool currently assumes a flat 180-day
  `days_to_expiry` for every donor (`backend/app/routers/redistribution_router.py`)
  since no real expiry-date dataset exists per facility-drug lot; wiring in
  real batch/expiry data (if e-Aushadhi exposes it) would make the
  `w3*(1/days_to_expiry)` term meaningful rather than constant.
- The real-weather route derating in `ml/matching.py` (heavy rain inflates
  effective travel time) uses each donor district's single most recent
  Open-Meteo observation, not a forecast of conditions on the day a
  transfer would actually happen. Wiring in `weather_forecast_16day.csv`
  instead would make the feasibility check forward-looking rather than
  same-day.
- Offline stock-report queueing in `StockReportForm.tsx` is a client-side
  localStorage queue with no background sync-on-reconnect listener yet --
  it queues correctly but won't auto-flush until the form is submitted
  again while online.
- Bottom-up transfer requests (`TransferRequest` in `backend/app/db.py`)
  are resolved manually by a district/state/national account; there's no
  automatic match-and-suggest step yet linking a new pending request to
  the same `rank_redistribution_candidates` ranking shown in the top-down
  view, beyond carrying over the facility's own suggested donor if given.
- No automated test suite yet (unit tests for `ml/*` scoring functions,
  integration tests for the FastAPI routes).
