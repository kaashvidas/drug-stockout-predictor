from fastapi import APIRouter, Depends

from app.auth import get_current_user, User
from app.data_store import scope_facilities, load_nlem_catalog, load_cag_ground_truth

router = APIRouter(prefix="/api/facilities", tags=["facilities"])


@router.get("")
def list_facilities(current_user: User = Depends(get_current_user)):
    return scope_facilities(current_user.role, current_user.scope).to_dict(orient="records")


@router.get("/drugs")
def drug_catalog():
    """Real NLEM 2022 catalog (see docs/DATA_SOURCES.md)."""
    return load_nlem_catalog()


@router.get("/ground-truth")
def ground_truth():
    """Real CAG audit figures used as calibration checkpoints."""
    return load_cag_ground_truth()
