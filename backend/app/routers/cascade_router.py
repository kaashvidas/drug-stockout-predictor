from fastapi import APIRouter, Depends

from app.auth import get_current_user, User
from app.data_store import load_current_risk_snapshot, load_facilities as _lf
from ml.cascade import build_facility_graph, propagate_stress, top_propagation_paths

router = APIRouter(prefix="/api/cascade", tags=["cascade"])

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_facility_graph()
    return _graph


@router.get("/{facility_id}/{drug}")
def cascade_for_facility_drug(facility_id: str, drug: str, current_user: User = Depends(get_current_user)):
    """Own stress vs. propagated stress for THIS SPECIFIC drug, and the
    strongest propagation paths to/from neighbors sharing this facility's
    catchment (Section 05 diagram).

    Computed per (facility, drug) rather than the worst drug at each
    facility: every facility in this dataset carries some permanently
    critical drug somewhere in its 24-drug basket (e.g. the real, persistent
    Deferoxamine shortage), so a facility-wide "own_stress = max risk across
    all drugs" saturates at ~100% everywhere before any propagation even
    happens -- that made the cascade panel meaningless. Scoping to the
    selected drug gives the genuine, varying signal the diagram is supposed
    to show."""
    risk = load_current_risk_snapshot()
    drug_risk = risk[risk["drug"] == drug]
    own_stress = drug_risk.set_index("facility_id")["risk_probability"].to_dict()

    graph = get_graph()
    propagated = propagate_stress(graph, own_stress) if facility_id in graph.nodes else {}
    paths = top_propagation_paths(graph, facility_id, own_stress) if facility_id in graph.nodes else []

    facilities = _lf().set_index("facility_id")
    for p in paths:
        if p["to"] in facilities.index:
            p["facility_name"] = facilities.loc[p["to"], "facility_name"]

    return {
        "facility_id": facility_id,
        "drug": drug,
        "own_stress": float(own_stress.get(facility_id, 0.0)),
        "propagated_stress": float(propagated.get(facility_id, own_stress.get(facility_id, 0.0))),
        "neighbor_propagation_paths": paths,
    }
