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
