"""
Redistribution / matching engine (build guide Section 05):

    score(donor, recipient, drug) = w1*urgency(recipient)
                                   + w2*(1/travel_time)
                                   + w3*(1/days_to_expiry)
                                   - w4*donor_shortfall_risk

Ranked, top-k candidates only -- recommend-only, never auto-executed.
"""
from dataclasses import dataclass

W1_URGENCY = 0.45
W2_TRAVEL = 0.25
W3_EXPIRY = 0.15
W4_DONOR_RISK = 0.15

DEFAULT_DAYS_TO_EXPIRY = 180  # used when expiry data is unavailable


@dataclass
class RedistributionCandidate:
    donor_facility_id: str
    recipient_facility_id: str
    drug: str
    score: float
    travel_time_min: float
    urgency: float
    donor_shortfall_risk: float
    donor_surplus_days_of_cover: float


def score_candidate(
    urgency: float,
    travel_time_min: float,
    days_to_expiry: float,
    donor_shortfall_risk: float,
) -> float:
    urgency = max(0.0, min(1.0, urgency))
    donor_shortfall_risk = max(0.0, min(1.0, donor_shortfall_risk))
    travel_term = 1.0 / max(travel_time_min, 1.0)
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
    top_k: int = 5,
) -> list[RedistributionCandidate]:
    """donor_pool: list of {facility_id, days_of_cover, shortfall_risk, days_to_expiry}
    for facilities with surplus stock of `drug`. travel_times: donor_facility_id -> minutes."""
    candidates = []
    for donor in donor_pool:
        if donor["facility_id"] == recipient_facility_id:
            continue
        tt = travel_times.get(donor["facility_id"])
        if tt is None:
            continue
        expiry = donor.get("days_to_expiry", DEFAULT_DAYS_TO_EXPIRY)
        s = score_candidate(urgency, tt, expiry, donor["shortfall_risk"])
        candidates.append(
            RedistributionCandidate(
                donor_facility_id=donor["facility_id"],
                recipient_facility_id=recipient_facility_id,
                drug=drug,
                score=s,
                travel_time_min=tt,
                urgency=urgency,
                donor_shortfall_risk=donor["shortfall_risk"],
                donor_surplus_days_of_cover=donor["days_of_cover"],
            )
        )
    candidates.sort(key=lambda c: -c.score)
    return candidates[:top_k]
