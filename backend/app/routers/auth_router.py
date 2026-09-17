from fastapi import APIRouter, HTTPException, status

from app.auth import authenticate, create_access_token
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = create_access_token(user)
    return LoginResponse(access_token=token, role=user.role, scope=user.scope, display_name=user.display_name)


@router.get("/demo-accounts")
def demo_accounts():
    """Lets the frontend show a 'log in as ...' picker for the demo instead of
    requiring judges to know credentials."""
    from app.auth import SEED_USERS

    return [
        {"username": u, "role": rec["role"], "scope": rec["scope"], "display_name": rec["display_name"], "password": "demo123"}
        for u, rec in SEED_USERS.items()
    ]
