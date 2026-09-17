from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, User
from app.db import get_session, log_audit, StockReport
from app.schemas import StockReportRequest

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("")
def submit_stock_report(body: StockReportRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """Low-connectivity stock-report form (Section 07, facility layer). In a
    real deployment this queues offline and syncs when online; the demo
    stores it directly and logs it to the shared audit trail."""
    report = StockReport(
        facility_id=body.facility_id, drug=body.drug, reported_stock=body.reported_stock,
        reported_by=current_user.username, synced=True,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    log_audit(db, current_user.username, current_user.role, "stock_report_submitted",
              detail=f"{body.facility_id} / {body.drug} = {body.reported_stock}")
    return {"status": "submitted", "report_id": report.id}


@router.get("/{facility_id}")
def list_reports(facility_id: str, db: Session = Depends(get_session)):
    from app.db import StockReport as SR

    reports = db.query(SR).filter(SR.facility_id == facility_id).order_by(SR.created_at.desc()).limit(50).all()
    return [
        {"id": r.id, "drug": r.drug, "reported_stock": r.reported_stock, "reported_by": r.reported_by,
         "created_at": r.created_at.isoformat()}
        for r in reports
    ]
