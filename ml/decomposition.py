"""
STL decomposition module (build guide Section 05):

    y(t) = T(t) + S(t) + R(t)
    structural risk  <=>  slope(T, last W weeks) < -theta
    temporary dip    <=>  decline confined to S(t) or R(t)

Operates on the daily consumption series for a single facility-drug pair.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

TREND_WINDOW_WEEKS = 8
STRUCTURAL_SLOPE_THRESHOLD = -0.02  # fraction of mean trend level, per day


@dataclass
class DecompositionResult:
    trend: np.ndarray
    seasonal: np.ndarray
    resid: np.ndarray
    trend_slope_per_day: float
    is_structural_decline: bool
    dates: pd.DatetimeIndex


def decompose_series(dates: pd.Series, values: pd.Series, period: int = 7) -> DecompositionResult:
    """STL-decompose a daily series. Requires at least 2 full periods."""
    series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(dates))
    series = series.asfreq("D").interpolate(limit_direction="both")

    stl = STL(series, period=period, robust=True)
    res = stl.fit()

    window_days = TREND_WINDOW_WEEKS * 7
    trend_tail = res.trend.iloc[-window_days:]
    mean_level = trend_tail.mean() if trend_tail.mean() != 0 else 1.0
    x = np.arange(len(trend_tail))
    if len(trend_tail) >= 2:
        slope, _ = np.polyfit(x, trend_tail.values, 1)
        normalized_slope = slope / abs(mean_level)
    else:
        normalized_slope = 0.0

    is_structural = normalized_slope < STRUCTURAL_SLOPE_THRESHOLD

    return DecompositionResult(
        trend=res.trend.to_numpy(),
        seasonal=res.seasonal.to_numpy(),
        resid=res.resid.to_numpy(),
        trend_slope_per_day=float(normalized_slope),
        is_structural_decline=bool(is_structural),
        dates=series.index,
    )
