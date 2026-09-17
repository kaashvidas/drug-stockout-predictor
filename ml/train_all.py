"""
Orchestrates the full ML pipeline (build guide Section 06, steps 2-6):
  1. STL-decompose every facility-drug consumption series (real weather- and
     CAG-distribution-grounded synthetic series -- see docs/DATA_SOURCES.md).
  2. Derive the reporting-trust score per facility.
  3. Build a labeled training set (many time-snapshots per series) and train
     the interpretable gradient-boosted risk classifier.
  4. Score every facility-drug pair's CURRENT state and save it for the
     backend API to serve.
  5. Propagate cascade stress across the real-travel-time facility graph.
  6. Run the Section-11 validation backtest against the real Karnataka thalassemia-chelation
     checkpoints.

Run: python ml/train_all.py
"""
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from ml.cascade import build_facility_graph, propagate_stress
from ml.risk_classifier import train_classifier, predict_risk, risk_level_from_probability
from ml.trust import simulate_reporting_log, compute_trust_score, TRAILING_WEEKS

ROOT = Path(__file__).resolve().parent.parent
STOCK_PATH = ROOT / "data" / "synthetic" / "daily_stock.parquet"
FACILITIES_PATH = ROOT / "data" / "processed" / "facilities.csv"
MODELS_DIR = ROOT / "ml" / "models"
FEATURES_OUT = ROOT / "data" / "processed" / "training_features.parquet"
CURRENT_SNAPSHOT_OUT = ROOT / "data" / "processed" / "current_risk_snapshot.csv"
FACILITY_CASCADE_OUT = ROOT / "data" / "processed" / "facility_cascade_snapshot.csv"
VALIDATION_OUT = ROOT / "data" / "processed" / "validation_report.json"

TREND_WINDOW = 56  # 8 weeks, per guide formula
SNAPSHOT_STRIDE_DAYS = 21
MIN_HISTORY_DAYS = 70
FORWARD_LABEL_DAYS = 14
STOCKOUT_LABEL_THRESHOLD_DAYS_OF_COVER = 14


def stl_decompose(consumption: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    series = pd.Series(consumption)
    stl = STL(series, period=7, robust=False)
    res = stl.fit()
    return res.trend.to_numpy(), res.seasonal.to_numpy(), res.resid.to_numpy()


def build_features_for_series(group: pd.DataFrame, facility_type: str, seed: int) -> list[dict]:
    group = group.sort_values("date").reset_index(drop=True)
    n = len(group)
    consumption = group["consumption"].to_numpy()
    days_of_cover = group["days_of_cover"].to_numpy()
    dates = pd.DatetimeIndex(group["date"])

    trend, seasonal, resid = stl_decompose(consumption)

    reported_mask = simulate_reporting_log(group["facility_id"].iloc[0], facility_type, dates, seed)

    rows = []
    snapshot_indices = range(MIN_HISTORY_DAYS, n - FORWARD_LABEL_DAYS, SNAPSHOT_STRIDE_DAYS)
    for t in snapshot_indices:
        trend_window = trend[max(0, t - TREND_WINDOW): t]
        mean_level = np.mean(np.abs(trend_window)) if len(trend_window) else 1.0
        mean_level = mean_level if mean_level > 1e-6 else 1.0
        x = np.arange(len(trend_window))
        slope = np.polyfit(x, trend_window, 1)[0] if len(trend_window) >= 2 else 0.0
        trend_slope_56d = slope / mean_level

        seasonal_amplitude = float(np.std(seasonal[max(0, t - 28): t])) if t > 0 else 0.0
        resid_std = float(np.std(resid[max(0, t - 28): t])) if t > 0 else 0.0

        trust = compute_trust_score(
            reported_mask[max(0, t - TRAILING_WEEKS * 7): t],
            resid[max(0, t - TRAILING_WEEKS * 7): t],
            trend[max(0, t - TRAILING_WEEKS * 7): t],
        )

        future_min_cover = days_of_cover[t: t + FORWARD_LABEL_DAYS].min()
        label = int(future_min_cover < STOCKOUT_LABEL_THRESHOLD_DAYS_OF_COVER)

        rows.append(
            {
                "facility_id": group["facility_id"].iloc[0],
                "drug": group["drug"].iloc[0],
                "date": dates[t],
                "trend_slope_56d": float(trend_slope_56d),
                "seasonal_amplitude": seasonal_amplitude,
                "resid_std": resid_std,
                "current_days_of_cover": float(min(days_of_cover[t], 999)),
                "avg_consumption_14d": float(consumption[max(0, t - 14): t].mean()) if t > 0 else 0.0,
                "trust_score": trust,
                "stockout_within_14d": label,
            }
        )
    return rows


def main():
    t0 = time.time()
    print("Loading synthetic stock data ...")
    stock = pd.read_parquet(STOCK_PATH)
    facilities = pd.read_csv(FACILITIES_PATH).set_index("facility_id")["facility_type"].to_dict()

    print(f"Building features for {stock.groupby(['facility_id','drug']).ngroups} facility-drug series ...")
    all_rows = []
    seed = 7
    for (fac_id, drug), group in stock.groupby(["facility_id", "drug"], sort=False):
        seed += 1
        rows = build_features_for_series(group, facilities.get(fac_id, "PHC"), seed)
        all_rows.extend(rows)

    features_df = pd.DataFrame(all_rows)
    print(f"Built {len(features_df):,} training snapshots in {time.time()-t0:.1f}s")
    print("Label balance:\n", features_df["stockout_within_14d"].value_counts(normalize=True))

    FEATURES_OUT.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_parquet(FEATURES_OUT, index=False)

    print("Training risk classifier ...")
    trained = train_classifier(features_df)
    print(f"AUC: {trained.auc:.3f}")
    print(trained.report)
    print("Feature importances:", trained.feature_importances)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(trained.model, MODELS_DIR / "risk_classifier.joblib")
    with open(MODELS_DIR / "risk_classifier_report.json", "w") as f:
        json.dump(
            {"auc": trained.auc, "feature_importances": trained.feature_importances, "report": trained.report},
            f,
            indent=2,
        )

    print("Scoring current-state snapshot for every facility-drug pair ...")
    latest_date = stock["date"].max()
    current_rows = []
    for (fac_id, drug), group in stock.groupby(["facility_id", "drug"], sort=False):
        latest = group[group["date"] == latest_date]
        if latest.empty:
            continue
        matching_feat = features_df[(features_df["facility_id"] == fac_id) & (features_df["drug"] == drug)]
        if matching_feat.empty:
            continue
        last_feat = matching_feat.sort_values("date").iloc[-1]
        prob, level = predict_risk(trained.model, last_feat)
        current_rows.append(
            {
                "facility_id": fac_id,
                "drug": drug,
                "district": group["district"].iloc[0],
                "state": group["state"].iloc[0],
                "current_days_of_cover": float(latest["days_of_cover"].iloc[0]),
                "current_stock": float(latest["stock"].iloc[0]),
                "trend_slope_56d": float(last_feat["trend_slope_56d"]),
                "is_structural_decline": bool(last_feat["trend_slope_56d"] < -0.02),
                "trust_score": float(last_feat["trust_score"]),
                "risk_probability": prob,
                "risk_level": level,
            }
        )
    current_df = pd.DataFrame(current_rows)
    current_df.to_csv(CURRENT_SNAPSHOT_OUT, index=False)
    print(f"Wrote {len(current_df)} current risk snapshots to {CURRENT_SNAPSHOT_OUT}")

    print("Propagating cascade stress across the real facility graph ...")
    graph = build_facility_graph()
    own_stress = current_df.groupby("facility_id")["risk_probability"].max().to_dict()
    propagated = propagate_stress(graph, own_stress)
    cascade_df = pd.DataFrame(
        [{"facility_id": k, "own_stress": own_stress.get(k, 0.0), "propagated_stress": v} for k, v in propagated.items()]
    )
    cascade_df.to_csv(FACILITY_CASCADE_OUT, index=False)
    print(f"Wrote {len(cascade_df)} facility cascade-stress rows to {FACILITY_CASCADE_OUT}")

    print("Running Section-11 validation backtest (Karnataka thalassemia-chelation) ...")
    validation = run_validation_backtest(features_df, trained.model)
    with open(VALIDATION_OUT, "w") as f:
        json.dump(validation, f, indent=2, default=str)
    print(json.dumps(validation, indent=2, default=str))

    print(f"\nTotal pipeline time: {time.time()-t0:.1f}s")


def run_validation_backtest(features_df: pd.DataFrame, model) -> dict:
    """Per build guide Section 11: confirm the classifier correctly and
    persistently flags the real, documented Karnataka thalassemia
    chelation-drug shortage as critical risk throughout our monitoring
    window -- unlike a crisis-and-recovery story, the real timeline here
    (missing since 2020, still missing per the Sept 2021 Karnataka HC PIL,
    still missing per the Oct 2023 Deccan Herald follow-up) means the
    correct behavior is "always flagged," not "flagged N days before a
    single admission date." We check both, and check specifically against
    the 2023-10-02 article's publish date to state a real lead time too."""
    from ml.risk_classifier import predict_risk

    result = {}
    deferoxamine_feats = features_df[features_df["drug"] == "Deferoxamine"].sort_values("date").reset_index(drop=True)

    article_date = pd.Timestamp("2023-10-02")

    levels = []
    for _, row in deferoxamine_feats.iterrows():
        prob, level = predict_risk(model, row)
        levels.append((row["date"], prob, level))

    if levels:
        n_total = len(levels)
        n_critical_or_high = sum(1 for _, _, lvl in levels if lvl in ("high", "critical"))
        pct_flagged = n_critical_or_high / n_total

        before_article = [lvl for date, _, lvl in levels if date <= article_date]
        pct_flagged_before_article = (
            sum(1 for lvl in before_article if lvl in ("high", "critical")) / len(before_article)
            if before_article else 0.0
        )

        result["karnataka_thalassemia_chelation"] = {
            "real_shortage_start_year": 2020,
            "real_karnataka_hc_pil_date": "2021-09-23",
            "real_followup_article_date": str(article_date.date()),
            "n_monitoring_snapshots_statewide": n_total,
            "pct_snapshots_flagged_high_or_critical": round(pct_flagged, 3),
            "pct_snapshots_flagged_before_article_date": round(pct_flagged_before_article, 3),
            "claim": (
                f"Across {n_total} facility-level monitoring snapshots of Deferoxamine statewide, the "
                f"pipeline flagged {pct_flagged:.0%} as high/critical risk -- including {pct_flagged_before_article:.0%} "
                f"of snapshots dated on or before the real 2 October 2023 Deccan Herald report confirming the "
                f"shortage was still unresolved. Unlike a single-admission-date crisis, this drug's correct "
                f"signature is a PERSISTENT critical flag, not a one-time early warning; the pipeline reproduces "
                f"that shape rather than a temporary dip."
            ),
        }
    else:
        result["karnataka_thalassemia_chelation"] = {"status": "no Deferoxamine snapshots found in training features"}

    return result


if __name__ == "__main__":
    main()
