# Next steps / known follow-ups

Things deliberately deferred rather than faked. See docs/DATA_SOURCES.md for
the full data-provenance detail behind each item.

## Data
- **NPPA sales volumes**: register a free API key at https://data.gov.in and
  wire it into a new `scripts/fetch_nppa.py`; currently no NPPA-derived
  number appears anywhere in this codebase.
- **IDSP weekly outbreak bulletins / Nikshay TB dashboards**: both are
  JS-rendered without a reachable flat-file export. `ml/fusion.py` already
  accepts an `idsp_signal` parameter and has the rule table wired — it just
  isn't fed live data yet. `scripts/fetch_travel_times.py` and
  `scripts/fetch_weather.py` are the pattern to follow once a real endpoint
  is found (or an official CSV export becomes available).
- **HMIS's own facility registry**: substituted with real OpenStreetMap
  facility data for the same 6 real districts (documented, not hidden). A
  real deployment would integrate the actual HMIS registry (2.17 lakh+
  facilities) via the same kind of MoU the build guide describes for Tier 3.

## Modeling
- The risk classifier's dominant feature is `current_days_of_cover` (importance
  ~0.995) rather than the STL trend slope -- meaning the "structural vs.
  temporary" distinction is currently surfaced as its own explicit boolean
  (`is_structural_decline`, from `ml/decomposition.py`'s slope threshold)
  alongside the ML probability, not fused into a single blended score. A
  richer label design (e.g., predicting *structural* decline specifically,
  not just "will cross 14 days-of-cover") would let trend_slope carry more
  weight in the classifier itself.
- The Section-11 validation backtest for Sarguja is implemented
  (`ml/train_all.py::run_validation_backtest`) with a 180-day monitoring
  window and a 2-consecutive-snapshot persistence requirement to avoid
  claiming credit for one-off noise. It currently reports the model
  persistently flagging high risk ~162 days before the real 18 March 2024
  Central TB Division admission -- a defensible claim, but the same
  backtest has not yet been extended to Pilibhit's exposure-based checkpoint.
- Cascade stress propagation is computed from a single current-state
  snapshot (3 diffusion iterations), not simulated day-by-day across the
  full 2-year history. A historical cascade backtest (did neighboring
  facilities' risk visibly rise before their own data showed decline?)
  would strengthen the "predicts spillover" claim with a concrete number.

## Backend / frontend
- Redistribution donor pool currently assumes a flat 180-day
  `days_to_expiry` for every donor (`backend/app/routers/redistribution_router.py`)
  since no real expiry-date dataset exists per facility-drug lot; wiring in
  real batch/expiry data (if a state's e-tracking system exposes it) would
  make the `w3*(1/days_to_expiry)` term meaningful rather than constant.
- Offline stock-report queueing in `StockReportForm.tsx` is a client-side
  localStorage queue with no background sync-on-reconnect listener yet --
  it queues correctly but won't auto-flush until the form is submitted
  again while online.
- No automated test suite yet (unit tests for `ml/*` scoring functions,
  integration tests for the FastAPI routes).
