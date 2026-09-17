"""
Risk classification (build guide Section 05 & 08): interpretable
gradient-boosted classifier predicting "will this facility-drug pair fall
below 14 days-of-cover within the next 14 days", trained on features derived
from real STL decomposition of each series (trend slope, seasonal amplitude,
residual noise), the reporting-trust score, and current stock position.

Feature importances are exposed directly (no black-box deep model) so every
alert can show which signal drove it -- the "why" panel the guide's frontend
principles ask for.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report

FEATURE_COLUMNS = [
    "trend_slope_56d",
    "seasonal_amplitude",
    "resid_std",
    "current_days_of_cover",
    "avg_consumption_14d",
    "trust_score",
]
LABEL_COLUMN = "stockout_within_14d"

RISK_LEVEL_THRESHOLDS = {"critical": 0.75, "high": 0.5, "medium": 0.25}


def risk_level_from_probability(p: float) -> str:
    if p >= RISK_LEVEL_THRESHOLDS["critical"]:
        return "critical"
    if p >= RISK_LEVEL_THRESHOLDS["high"]:
        return "high"
    if p >= RISK_LEVEL_THRESHOLDS["medium"]:
        return "medium"
    return "low"


@dataclass
class TrainedModel:
    model: GradientBoostingClassifier
    feature_importances: dict[str, float]
    auc: float
    report: str


def train_classifier(features_df: pd.DataFrame) -> TrainedModel:
    X = features_df[FEATURE_COLUMNS]
    y = features_df[LABEL_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    report = classification_report(y_test, model.predict(X_test))

    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))

    return TrainedModel(model=model, feature_importances=importances, auc=auc, report=report)


def predict_risk(model: GradientBoostingClassifier, features_row: pd.Series) -> tuple[float, str]:
    X = features_row[FEATURE_COLUMNS].to_frame().T
    prob = model.predict_proba(X)[0, 1]
    return float(prob), risk_level_from_probability(prob)
