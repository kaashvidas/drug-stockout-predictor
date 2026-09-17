from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    scope: str
    display_name: str


class ApproveRedistributionRequest(BaseModel):
    donor_facility_id: str
    recipient_facility_id: str
    drug: str
    score: float
    travel_time_min: float


class StockReportRequest(BaseModel):
    facility_id: str
    drug: str
    reported_stock: float
    status: str = "normal"  # normal | surplus | critical


class TransferRequestCreate(BaseModel):
    requesting_facility_id: str
    drug: str
    suggested_donor_facility_id: str | None = None
    note: str | None = None


class TransferRequestResolve(BaseModel):
    action: str  # approve | dismiss
    donor_facility_id: str | None = None
