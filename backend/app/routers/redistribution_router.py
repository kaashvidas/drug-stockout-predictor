from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, User
from app.data_store import load_current_risk_snapshot, load_travel_times, load_facilities, load_latest_weather_by_district
from app.db import get_session, log_audit, RedistributionApproval, TransferRequest
from app.schemas import ApproveRedistributionRequest, TransferRequestCreate, TransferRequestResolve
from ml.matching import rank_redistribution_candidates
from sqlalchemy.orm import Session
from fastapi import Depends as FDepends

router = APIRouter(prefix="/api/redistribution", tags=["redistribution"])

DAYS_OF_COVER_SURPLUS_THRESHOLD = 45


def _build_candidates(facility_id: str, drug: str, top_k: int = 5):
    """Shared by /recommendations and the transfer-request flow so a
    facility's own 'request supply' suggestion uses the same real
    travel-time + real-weather-derated scoring as the top-down view."""
    risk = load_current_risk_snapshot()
    recipient_rows = risk[(risk["facility_id"] == facility_id) & (risk["drug"] == drug)]
    if recipient_rows.empty:
        return None, None
    urgency = float(recipient_rows["risk_probability"].iloc[0])

    same_drug = risk[risk["drug"] == drug]
    donor_rows = same_drug[same_drug["current_days_of_cover"] >= DAYS_OF_COVER_SURPLUS_THRESHOLD]

    donor_pool = [
        {
            "facility_id": r["facility_id"],
            "days_of_cover": r["current_days_of_cover"],
            "shortfall_risk": r["risk_probability"],
            "days_to_expiry": 180,
        }
        for _, r in donor_rows.iterrows()
    ]

    travel = load_travel_times()
    travel_from_donors = travel[travel["facility_id_to"] == facility_id].set_index("facility_id_from")["travel_time_min"].to_dict()

    facilities = load_facilities().set_index("facility_id")
    weather_by_district = load_latest_weather_by_district()
    donor_rain_mm = {}
    for donor_id in travel_from_donors:
        if donor_id in facilities.index:
            d = facilities.loc[donor_id, "district"]
            donor_rain_mm[donor_id] = weather_by_district.get(d, {}).get("rain_mm", 0.0)

    candidates = rank_redistribution_candidates(
        facility_id, drug, urgency, donor_pool, travel_from_donors, donor_rain_mm=donor_rain_mm, top_k=top_k
    )
    return candidates, facilities


@router.get("/recommendations")
def recommendations(facility_id: str, drug: str, current_user: User = Depends(get_current_user)):
    """Ranked, top-k feasible redistribution candidates for a recipient
    facility-drug pair, with routes derated for real heavy rain on the
    donor's side. Recommend-only -- never auto-executed (Section 05)."""
    candidates, facilities = _build_candidates(facility_id, drug)
    if candidates is None:
        raise HTTPException(status_code=404, detail="No risk record for this facility-drug pair")

    out = []
    for c in candidates:
        row = c.__dict__.copy()
        if c.donor_facility_id in facilities.index:
            row["donor_facility_name"] = facilities.loc[c.donor_facility_id, "facility_name"]
            row["donor_district"] = facilities.loc[c.donor_facility_id, "district"]
        out.append(row)
    return out


@router.post("/approve")
def approve(body: ApproveRedistributionRequest, current_user: User = Depends(get_current_user), db: Session = FDepends(get_session)):
    if current_user.role not in ("district", "state", "national"):
        raise HTTPException(status_code=403, detail="Only district/state/national roles may approve a redistribution")

    approval = RedistributionApproval(
        donor_facility_id=body.donor_facility_id,
        recipient_facility_id=body.recipient_facility_id,
        drug=body.drug,
        score=body.score,
        travel_time_min=body.travel_time_min,
        approved_by=current_user.username,
        approved_role=current_user.role,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    log_audit(
        db, current_user.username, current_user.role, "redistribution_approved",
        detail=f"{body.donor_facility_id} -> {body.recipient_facility_id} ({body.drug})",
    )
    return {"status": "approved", "approval_id": approval.id}


@router.post("/requests")
def create_transfer_request(
    body: TransferRequestCreate, current_user: User = Depends(get_current_user), db: Session = FDepends(get_session)
):
    """Bottom-up request: a facility flags critical stock and asks for
    supply, optionally naming a specific nearby surplus facility (Section 07,
    facility layer: 'request the nearby facilities having a surplus')."""
    if current_user.role != "facility":
        raise HTTPException(status_code=403, detail="Only a facility account can raise a transfer request")

    req = TransferRequest(
        requesting_facility_id=body.requesting_facility_id,
        drug=body.drug,
        suggested_donor_facility_id=body.suggested_donor_facility_id,
        note=body.note,
        requested_by=current_user.username,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit(
        db, current_user.username, current_user.role, "transfer_requested",
        detail=f"{body.requesting_facility_id} requested {body.drug}"
        + (f" (suggested donor: {body.suggested_donor_facility_id})" if body.suggested_donor_facility_id else ""),
    )
    return {"status": "submitted", "request_id": req.id}


@router.get("/requests")
def list_transfer_requests(
    status: str = "pending", current_user: User = Depends(get_current_user), db: Session = FDepends(get_session)
):
    """Pending queue for procurement roles to act on (Section 05: 'a person
    approves every transfer'). Facility accounts see only their own."""
    query = db.query(TransferRequest)
    if status != "all":
        query = query.filter(TransferRequest.status == status)
    if current_user.role == "facility":
        query = query.filter(TransferRequest.requesting_facility_id == current_user.scope)
    elif current_user.role not in ("district", "state", "national"):
        raise HTTPException(status_code=403, detail="Not authorized to view transfer requests")

    facilities = load_facilities().set_index("facility_id")
    out = []
    for r in query.order_by(TransferRequest.created_at.desc()).limit(200).all():
        row = {
            "id": r.id, "requesting_facility_id": r.requesting_facility_id, "drug": r.drug,
            "suggested_donor_facility_id": r.suggested_donor_facility_id, "note": r.note,
            "requested_by": r.requested_by, "status": r.status, "resolved_by": r.resolved_by,
            "resolved_donor_facility_id": r.resolved_donor_facility_id,
            "created_at": r.created_at.isoformat(),
        }
        if r.requesting_facility_id in facilities.index:
            row["requesting_facility_name"] = facilities.loc[r.requesting_facility_id, "facility_name"]
            row["requesting_district"] = facilities.loc[r.requesting_facility_id, "district"]
        out.append(row)
    return out


@router.post("/requests/{request_id}/resolve")
def resolve_transfer_request(
    request_id: int, body: TransferRequestResolve, current_user: User = Depends(get_current_user), db: Session = FDepends(get_session)
):
    if current_user.role not in ("district", "state", "national"):
        raise HTTPException(status_code=403, detail="Only district/state/national roles may resolve a transfer request")

    req = db.query(TransferRequest).filter(TransferRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Transfer request not found")

    if body.action == "approve":
        req.status = "approved"
        req.resolved_donor_facility_id = body.donor_facility_id or req.suggested_donor_facility_id
    else:
        req.status = "dismissed"
    req.resolved_by = current_user.username
    from datetime import datetime, timezone

    req.resolved_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(
        db, current_user.username, current_user.role, f"transfer_request_{req.status}",
        detail=f"request #{request_id} ({req.requesting_facility_id} / {req.drug})"
        + (f", donor: {req.resolved_donor_facility_id}" if req.resolved_donor_facility_id else ""),
    )
    return {"status": req.status}


@router.get("/audit-log")
def audit_log(current_user: User = Depends(get_current_user), db: Session = FDepends(get_session)):
    if current_user.role not in ("district", "state", "national"):
        raise HTTPException(status_code=403, detail="Not authorized to view the audit log")
    from app.db import AuditLogEntry

    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(200).all()
    return [
        {
            "id": e.id, "actor": e.actor_username, "role": e.actor_role, "action": e.action,
            "detail": e.detail, "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
