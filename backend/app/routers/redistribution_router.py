from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, User
from app.data_store import load_current_risk_snapshot, load_travel_times, load_facilities
from app.db import get_session, log_audit, RedistributionApproval
from app.schemas import ApproveRedistributionRequest
from ml.matching import rank_redistribution_candidates
from sqlalchemy.orm import Session
from fastapi import Depends as FDepends

router = APIRouter(prefix="/api/redistribution", tags=["redistribution"])

DAYS_OF_COVER_SURPLUS_THRESHOLD = 45


@router.get("/recommendations")
def recommendations(facility_id: str, drug: str, current_user: User = Depends(get_current_user)):
    """Ranked, top-k feasible redistribution candidates for a recipient
    facility-drug pair. Recommend-only -- never auto-executed (Section 05)."""
    risk = load_current_risk_snapshot()
    recipient_rows = risk[(risk["facility_id"] == facility_id) & (risk["drug"] == drug)]
    if recipient_rows.empty:
        raise HTTPException(status_code=404, detail="No risk record for this facility-drug pair")
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

    candidates = rank_redistribution_candidates(facility_id, drug, urgency, donor_pool, travel_from_donors)

    facilities = load_facilities().set_index("facility_id")
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
