from fastapi import APIRouter, Depends

from app.auth import get_current_user, User
from app.data_store import (
    scope_risk_snapshot, scope_facilities, load_daily_stock_for, load_validation_report, DRUG_TO_CATEGORY,
    load_travel_times,
)
from ml.decomposition import decompose_series
from ml.forecasting import forecast_consumption, apply_real_weather_fusion, project_days_of_cover

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts(current_user: User = Depends(get_current_user)):
    """Ranked alert list, scoped by role -- same underlying evidence at every level (Section 07)."""
    risk = scope_risk_snapshot(current_user.role, current_user.scope)
    facilities = scope_facilities(current_user.role, current_user.scope)
    risk = risk.merge(facilities[["facility_id", "facility_name", "facility_type"]], on="facility_id", how="left")
    risk = risk.sort_values("risk_probability", ascending=False)
    return risk.to_dict(orient="records")


@router.get("/rankings/by-drug")
def rankings_by_drug(current_user: User = Depends(get_current_user)):
    """Which DRUGS are most at risk across every facility in scope -- the
    cross-facility ranked view a national task force or vertical program
    needs (as opposed to the per-facility alert list)."""
    risk = scope_risk_snapshot(current_user.role, current_user.scope)
    if risk.empty:
        return []
    agg = (
        risk.groupby(["drug", "drug_category"])
        .agg(
            avg_risk=("risk_probability", "mean"),
            max_risk=("risk_probability", "max"),
            n_critical=("risk_level", lambda s: (s == "critical").sum()),
            n_high=("risk_level", lambda s: (s == "high").sum()),
            n_facilities=("facility_id", "nunique"),
            n_structural_decline=("is_structural_decline", "sum"),
        )
        .reset_index()
        .sort_values("avg_risk", ascending=False)
    )
    return agg.to_dict(orient="records")


@router.get("/rankings/by-facility")
def rankings_by_facility(current_user: User = Depends(get_current_user)):
    """Which FACILITIES are most at risk across their whole drug basket --
    the ranked shortlist a program manager or task force acts on first."""
    risk = scope_risk_snapshot(current_user.role, current_user.scope)
    facilities = scope_facilities(current_user.role, current_user.scope)
    if risk.empty:
        return []
    agg = (
        risk.groupby("facility_id")
        .agg(
            avg_risk=("risk_probability", "mean"),
            max_risk=("risk_probability", "max"),
            n_critical=("risk_level", lambda s: (s == "critical").sum()),
            n_high=("risk_level", lambda s: (s == "high").sum()),
            n_drugs=("drug", "nunique"),
            worst_drug=("drug", lambda s: s.loc[risk.loc[s.index, "risk_probability"].idxmax()]),
        )
        .reset_index()
        .sort_values("max_risk", ascending=False)
    )
    agg = agg.merge(facilities[["facility_id", "facility_name", "facility_type", "district", "state"]], on="facility_id", how="left")
    return agg.to_dict(orient="records")


@router.get("/heatmap")
def heatmap(current_user: User = Depends(get_current_user)):
    """District/state aggregated risk for the map view (Section 09: heatmap first)."""
    risk = scope_risk_snapshot(current_user.role, current_user.scope)
    facilities = scope_facilities(current_user.role, current_user.scope)
    merged = risk.merge(facilities[["facility_id", "lat", "lon", "facility_name", "facility_type"]], on="facility_id", how="left")
    agg = (
        merged.groupby(["district", "state"])
        .agg(
            avg_risk=("risk_probability", "mean"),
            max_risk=("risk_probability", "max"),
            n_critical=("risk_level", lambda s: (s == "critical").sum()),
            n_high=("risk_level", lambda s: (s == "high").sum()),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
        .reset_index()
    )
    return agg.to_dict(orient="records")


@router.get("/availability/{drug}")
def availability(drug: str, near_facility_id: str | None = None, current_user: User = Depends(get_current_user)):
    """Availability-lookup tool for distributors/procurement roles: this
    drug's stock/days-of-cover at every facility in scope, and -- if
    near_facility_id is given -- ranked by real travel time from that
    facility, so a procurement officer can see 'what's the availability of
    this drug nearby' at any time, not only when the system itself flags a
    shortage."""
    risk = scope_risk_snapshot(current_user.role, current_user.scope)
    risk = risk[risk["drug"] == drug]
    facilities = scope_facilities(current_user.role, current_user.scope)
    merged = risk.merge(
        facilities[["facility_id", "facility_name", "facility_type", "lat", "lon"]], on="facility_id", how="left"
    )

    if near_facility_id:
        travel = load_travel_times()
        tt = travel[travel["facility_id_to"] == near_facility_id].set_index("facility_id_from")["travel_time_min"].to_dict()
        merged["travel_time_min"] = merged["facility_id"].map(tt)
        merged = merged[merged["facility_id"] != near_facility_id]
        merged = merged.sort_values(["travel_time_min", "risk_probability"], na_position="last")
    else:
        merged = merged.sort_values("risk_probability")

    return merged.to_dict(orient="records")


@router.get("/{facility_id}/{drug}/explain")
def explain_alert(facility_id: str, drug: str, current_user: User = Depends(get_current_user)):
    """Drill-down explainability panel: real STL decomposition of this pair's
    consumption series, plus its current risk score and trust band (Section 09)."""
    df = load_daily_stock_for(facility_id, drug)
    if df.empty:
        return {"error": "no data for this facility-drug pair"}

    result = decompose_series(df["date"], df["consumption"])
    risk_row = scope_risk_snapshot("national", "all")
    risk_row = risk_row[(risk_row["facility_id"] == facility_id) & (risk_row["drug"] == drug)]

    return {
        "facility_id": facility_id,
        "drug": drug,
        "drug_category": DRUG_TO_CATEGORY.get(drug),
        "dates": [d.strftime("%Y-%m-%d") for d in result.dates],
        "consumption": df["consumption"].tolist(),
        "stock": df["stock"].tolist(),
        "days_of_cover": df["days_of_cover"].tolist(),
        "trend": result.trend.tolist(),
        "seasonal": result.seasonal.tolist(),
        "residual": result.resid.tolist(),
        "trend_slope_per_day": result.trend_slope_per_day,
        "is_structural_decline": result.is_structural_decline,
        "current_risk": risk_row.to_dict(orient="records")[0] if not risk_row.empty else None,
        "reconstructed_notice": (
            "Stock and consumption values on this chart are reconstructed -- interpolated between "
            "verified checkpoints (real CAG Karnataka audit percentages; the real, dated 2020-onward "
            "Desferal/thalassemia shortage where this pair is that drug). See docs/DATA_SOURCES.md."
        ),
    }


@router.get("/{facility_id}/{drug}/forecast")
def forecast_alert(facility_id: str, drug: str, current_user: User = Depends(get_current_user)):
    """16-day Prophet forecast, fused with the REAL live Open-Meteo 16-day
    weather forecast for this facility's district (Section 05 leading-
    indicator fusion, Section 08 Prophet). Projects a stockout date at the
    current stock level assuming no further resupply."""
    df = load_daily_stock_for(facility_id, drug)
    if df.empty:
        return {"error": "no data for this facility-drug pair"}

    district = df["district"].iloc[0]
    drug_category = DRUG_TO_CATEGORY.get(drug, "other")
    current_stock = float(df["stock"].iloc[-1])

    raw_forecast = forecast_consumption(df["date"], df["consumption"])
    fused = apply_real_weather_fusion(raw_forecast, district, drug_category)
    projected = project_days_of_cover(current_stock, fused)

    projected_stockout_date = None
    zero_rows = projected[projected["projected_stock"] <= 0]
    if not zero_rows.empty:
        projected_stockout_date = zero_rows.iloc[0]["ds"].strftime("%Y-%m-%d")

    return {
        "facility_id": facility_id,
        "drug": drug,
        "district": district,
        "current_stock": current_stock,
        "forecast": [
            {
                "date": r["ds"].strftime("%Y-%m-%d"),
                "forecasted_consumption": float(r["yhat_fused"]),
                "weather_multiplier": float(r["weather_multiplier"]),
                "projected_stock": float(r["projected_stock"]),
            }
            for _, r in projected.iterrows()
        ],
        "projected_stockout_date": projected_stockout_date,
        "weather_source": "Open-Meteo live 16-day forecast (real, fetched by scripts/fetch_weather.py)",
    }


@router.get("/validation-report")
def validation_report():
    """Section 11: the backtest claim, not an invented accuracy number."""
    return load_validation_report()
