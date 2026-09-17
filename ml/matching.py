"""
Redistribution / matching engine (build guide Section 05):

    score(donor, recipient, drug) = w1*urgency(recipient)
                                   + w2*(1/travel_time)
                                   + w3*(1/days_to_expiry)
                                   - w4*donor_shortfall_risk

Ranked, top-k candidates only -- recommend-only, never auto-executed.

Route feasibility is adjusted by REAL weather on the donor's district
(Open-Meteo, the same live data the forecast fusion module uses) -- heavy
real rain inflates the effective travel time used in scoring, since a
flooded or slow route is a genuine feasibility risk a procurement officer
would actually weigh, not just raw OSRM minutes under clear conditions.
"""
from dataclasses import dataclass

W1_URGENCY = 0.45
W2_TRAVEL = 0.25
W3_EXPIRY = 0.15
W4_DONOR_RISK = 0.15

DEFAULT_DAYS_TO_EXPIRY = 180  # used when expiry data is unavailable

HEAVY_RAIN_MM_THRESHOLD = 20.0
WEATHER_DERATE_FACTOR = 1.6  # effective travel time multiplier under heavy real rain


@dataclass
class RedistributionCandidate:
    donor_facility_id: str
    recipient_facility_id: str
    drug: str
    score: float
    travel_time_min: float
    effective_travel_time_min: float
    weather_flag: bool
    urgency: float
    donor_shortfall_risk: float
    donor_surplus_days_of_cover: float


def effective_travel_time(travel_time_min: float, donor_rain_mm: float) -> tuple[float, bool]:
    if donor_rain_mm >= HEAVY_RAIN_MM_THRESHOLD:
        return travel_time_min * WEATHER_DERATE_FACTOR, True
    return travel_time_min, False


def score_candidate(
    urgency: float,
    effective_travel_time_min: float,
    days_to_expiry: float,
    donor_shortfall_risk: float,
) -> float:
    urgency = max(0.0, min(1.0, urgency))
    donor_shortfall_risk = max(0.0, min(1.0, donor_shortfall_risk))
    travel_term = 1.0 / max(effective_travel_time_min, 1.0)
    expiry_term = 1.0 / max(days_to_expiry, 1.0)

    return (
        W1_URGENCY * urgency
        + W2_TRAVEL * travel_term
        - W4_DONOR_RISK * donor_shortfall_risk
        + W3_EXPIRY * expiry_term
    )


def rank_redistribution_candidates(
    recipient_facility_id: str,
    drug: str,
    urgency: float,
    donor_pool: list[dict],
    travel_times: dict[str, float],
    donor_rain_mm: dict[str, float] | None = None,
    top_k: int = 5,
) -> list[RedistributionCandidate]:
    """donor_pool: list of {facility_id, days_of_cover, shortfall_risk, days_to_expiry}
    for facilities with surplus stock of `drug`. travel_times: donor_facility_id -> minutes.
    donor_rain_mm: donor_facility_id -> today's real rain_mm at that donor's district (optional)."""
    donor_rain_mm = donor_rain_mm or {}
    candidates = []
    for donor in donor_pool:
        if donor["facility_id"] == recipient_facility_id:
            continue
        tt = travel_times.get(donor["facility_id"])
        if tt is None:
            continue
        rain = donor_rain_mm.get(donor["facility_id"], 0.0)
        eff_tt, flagged = effective_travel_time(tt, rain)
        expiry = donor.get("days_to_expiry", DEFAULT_DAYS_TO_EXPIRY)
        s = score_candidate(urgency, eff_tt, expiry, donor["shortfall_risk"])
        candidates.append(
            RedistributionCandidate(
                donor_facility_id=donor["facility_id"],
                recipient_facility_id=recipient_facility_id,
                drug=drug,
                score=s,
                travel_time_min=tt,
                effective_travel_time_min=eff_tt,
                weather_flag=flagged,
                urgency=urgency,
                donor_shortfall_risk=donor["shortfall_risk"],
                donor_surplus_days_of_cover=donor["days_of_cover"],
            )
        )
    candidates.sort(key=lambda c: -c.score)
    return candidates[:top_k]
