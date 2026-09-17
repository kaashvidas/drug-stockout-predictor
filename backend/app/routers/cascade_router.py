from fastapi import APIRouter, Depends

from app.auth import get_current_user, User
from app.data_store import load_cascade_snapshot, load_facilities as _lf
from ml.cascade import build_facility_graph, top_propagation_paths

router = APIRouter(prefix="/api/cascade", tags=["cascade"])

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_facility_graph()
    return _graph


@router.get("/{facility_id}")
def cascade_for_facility(facility_id: str, current_user: User = Depends(get_current_user)):
    """Own stress vs. propagated stress, and the strongest propagation paths
    to/from neighbors sharing this facility's catchment (Section 05 diagram)."""
    snap = load_cascade_snapshot()
    row = snap[snap["facility_id"] == facility_id]
    graph = get_graph()
    own_stress = snap.set_index("facility_id")["own_stress"].to_dict()
    paths = top_propagation_paths(graph, facility_id, own_stress) if facility_id in graph.nodes else []

    facilities = _lf().set_index("facility_id")
    for p in paths:
        if p["to"] in facilities.index:
            p["facility_name"] = facilities.loc[p["to"], "facility_name"]

    return {
        "facility_id": facility_id,
        "own_stress": float(row["own_stress"].iloc[0]) if not row.empty else 0.0,
        "propagated_stress": float(row["propagated_stress"].iloc[0]) if not row.empty else 0.0,
        "neighbor_propagation_paths": paths,
    }
