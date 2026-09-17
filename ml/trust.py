"""
Reporting-trust layer (build guide Section 05):

    trust_i = 0.5 * (reports_received / reports_expected, trailing 8 wks)
            + 0.5 * (1 - revision_volatility_i)

No real per-facility reporting-compliance log exists in any dataset this
project could fetch (see docs/DATA_SOURCES.md) -- the guide's own Section 13
("Risks & mitigations") names "inconsistent facility-level reporting" as an
expected real-world condition, so a facility-reliability parameter has to be
assumed to demonstrate the trust layer at all. That assumption is isolated
to exactly two places in this file (RELIABILITY_BY_FACILITY_TYPE and the
seeded Bernoulli draw below) and documented here rather than silently
baked into the stock generator. revision_volatility is NOT assumed -- it is
computed directly from the real coefficient of variation of each series'
day-to-day consumption noise (statsmodels STL residual).
"""
import numpy as np
import pandas as pd

TRAILING_WEEKS = 8

# Modeling assumption (see module docstring): base reporting reliability by
# facility tier, reflecting the guide's own stated real-world risk that
# smaller/lower-connectivity facilities report less consistently.
RELIABILITY_BY_FACILITY_TYPE = {
    "District Hospital": 0.97,
    "CHC": 0.90,
    "PHC": 0.82,
    "Pharmacy/Dispensary": 0.75,
}


def simulate_reporting_log(facility_id: str, facility_type: str, dates: pd.DatetimeIndex, seed: int) -> np.ndarray:
    """Bernoulli reporting-compliance simulation (see module docstring)."""
    rng = np.random.default_rng(seed)
    p = RELIABILITY_BY_FACILITY_TYPE.get(facility_type, 0.85)
    return rng.uniform(0, 1, size=len(dates)) < p


def compute_trust_score(reported_mask: np.ndarray, resid: np.ndarray, trend_level: np.ndarray) -> float:
    """Compute trust_i over the trailing 8-week window ending at the last date."""
    window = TRAILING_WEEKS * 7
    tail_mask = reported_mask[-window:] if len(reported_mask) >= window else reported_mask
    reports_received = tail_mask.sum()
    reports_expected = len(tail_mask)
    reporting_completeness = reports_received / reports_expected if reports_expected else 0.0

    tail_resid = resid[-window:] if len(resid) >= window else resid
    tail_trend = trend_level[-window:] if len(trend_level) >= window else trend_level
    mean_trend = np.mean(np.abs(tail_trend)) if len(tail_trend) else 1.0
    mean_trend = mean_trend if mean_trend > 1e-6 else 1.0
    revision_volatility = float(np.std(tail_resid) / mean_trend)
    revision_volatility = min(1.0, revision_volatility)

    trust = 0.5 * reporting_completeness + 0.5 * (1 - revision_volatility)
    return float(np.clip(trust, 0.0, 1.0))
