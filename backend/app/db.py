"""
SQLite-backed audit trail and redistribution-approval log (build guide
Section 05: "one audit trail -- every alert and every approved redistribution
logged once, visible (scoped) at every level above it"). Read-heavy
analytical data lives in data_store.py instead -- this file is only for
state that changes as people use the app.
"""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent.parent / "shortage_cascade.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class RedistributionApproval(Base):
    __tablename__ = "redistribution_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    donor_facility_id = Column(String, nullable=False)
    recipient_facility_id = Column(String, nullable=False)
    drug = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    travel_time_min = Column(Float, nullable=False)
    approved_by = Column(String, nullable=False)
    approved_role = Column(String, nullable=False)
    status = Column(String, default="approved")  # approved | dismissed | confirmed_received
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_username = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    district = Column(String, nullable=True)
    state = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class StockReport(Base):
    """Facility-submitted stock counts (low-connectivity report form, Section 07)."""
    __tablename__ = "stock_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(String, nullable=False)
    drug = Column(String, nullable=False)
    reported_stock = Column(Float, nullable=False)
    reported_by = Column(String, nullable=False)
    synced = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_audit(db, actor_username: str, actor_role: str, action: str, detail: str = None, district: str = None, state: str = None):
    entry = AuditLogEntry(
        actor_username=actor_username, actor_role=actor_role, action=action,
        detail=detail, district=district, state=state,
    )
    db.add(entry)
    db.commit()
    return entry
