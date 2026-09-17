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


def _resolve_facility_id(district: str, fallback: str) -> str:
    try:
        from app.data_store import load_facilities

        fac = load_facilities()
        match = fac[fac["district"] == district]
        if not match.empty:
            return match.iloc[0]["facility_id"]
    except Exception:
        pass
    return fallback


class User(BaseModel):
    username: str
    role: str
    scope: str  # facility_id | district name | state name | drug_category | "all"
    display_name: str


# Seeded demo users -- one per role/scope, matching Karnataka's real
# districts and the real vertical-program drug basket this project
# fetched/curated. Ballari, Bengaluru Urban, Dharwad, Kolar and Mysuru are
# the 5 districts the real CAG audit itself test-checked (Table 4.5).
SEED_USERS: dict[str, dict] = {
    "ballari_pharmacist": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "facility",
        "scope": _resolve_facility_id("Ballari", "FAC0001"),
        "display_name": "Ballari Government Hospital Pharmacist",
    },
    "mysuru_district_pm": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "district",
        "scope": "Mysuru",
        "display_name": "Mysuru District Program Manager",
    },
    "ksmscl_state_officer": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "state",
        "scope": "Karnataka",
        "display_name": "KSMSCL State Procurement Officer",
    },
    "thalassemia_program": {
        "password_hash": pbkdf2_sha256.hash("demo123"),
        "role": "program",
        "scope": "thalassemia_chelation",
        "display_name": "Dept. of Health & Family Welfare -- Hemoglobinopathy Programme",
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
