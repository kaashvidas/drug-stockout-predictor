"""
JWT-based RBAC (build guide Section 08): five roles, seeded role table,
enough to demo five distinct portal views without building a full IAM
system. Passwords are demo-only (see seed_users below) -- not for production.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel

SECRET_KEY = os.environ.get("SHORTAGE_CASCADE_SECRET", "dev-only-secret-change-in-real-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

ROLES = ["facility", "district", "state", "program", "national"]


def _resolve_pilibhit_facility_id() -> str:
    try:
        from app.data_store import load_facilities

        fac = load_facilities()
        pilibhit = fac[fac["district"] == "Pilibhit"]
        if not pilibhit.empty:
            return pilibhit.iloc[0]["facility_id"]
    except Exception:
        pass
    return "FAC0121"


class User(BaseModel):
    username: str
    role: str
    scope: str  # facility_id | district name | state name | drug_category | "all"
    display_name: str


# Seeded demo users -- one per role/scope, matching the real districts and
# the real vertical-program drug basket this project fetched/curated.
SEED_USERS: dict[str, dict] = {
    "pilibhit_pharmacist": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "facility",
        "scope": _resolve_pilibhit_facility_id(),
        "display_name": "Pilibhit PHC Pharmacist",
    },
    "sarguja_district_pm": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "district",
        "scope": "Sarguja",
        "display_name": "Sarguja District Program Manager",
    },
    "tn_state_tnmsc": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "state",
        "scope": "Tamil Nadu",
        "display_name": "TNMSC State Procurement Officer",
    },
    "central_tb_division": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "program",
        "scope": "anti_tb",
        "display_name": "Central TB Division",
    },
    "national_task_force": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "national",
        "scope": "all",
        "display_name": "National Crisis Task Force",
    },
}


def authenticate(username: str, password: str) -> User | None:
    record = SEED_USERS.get(username)
    if not record or not pbkdf2_sha256.verify(password, record["password_hash"]):
        return None
    return User(username=username, role=record["role"], scope=record["scope"], display_name=record["display_name"])


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user.username, "role": user.role, "scope": user.scope, "name": user.display_name, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        return User(username=username, role=payload["role"], scope=payload["scope"], display_name=payload["name"])
    except JWTError:
        raise credentials_exception
