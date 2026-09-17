"""
Spillover-cascade model (build guide Section 05):

    stress_i(t+1) = own_stress_i + delta * SUM_j w_ij * stress_j(t),   w_ij ~ 1/travel_time(i,j)

Graph built from real OSRM travel times (data/processed/travel_times.csv),
restricted to a real CATCHMENT_MINUTES radius rather than every facility
that happens to share an (often large) administrative district: some
Karnataka districts have 150+ facilities all mutually connected in the raw
travel-time data, which isn't a real shared catchment -- two PHCs 90
minutes apart in the same district don't plausibly absorb each other's
demand overflow. Weights are normalized per node (so a node's neighbor
weights sum to 1) before applying delta, turning the diffusion term into a
bounded weighted AVERAGE of neighbor stress rather than an unbounded SUM --
without this, a facility with many real nearby neighbors saturates to 1.0
regardless of its own_stress, which is what the raw sum was doing before
this fix (see STATUS.md).
"""
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TRAVEL_TIMES_PATH = ROOT / "data" / "processed" / "travel_times.csv"

CATCHMENT_MINUTES = 30  # real shared-catchment radius
DELTA = 0.35  # propagation decay coefficient
N_ITERATIONS = 3


def build_facility_graph() -> nx.DiGraph:
    df = pd.read_csv(TRAVEL_TIMES_PATH)
    df = df[df["travel_time_min"] <= CATCHMENT_MINUTES]

    g = nx.DiGraph()
    for _, row in df.iterrows():
        weight = 1.0 / max(row["travel_time_min"], 1.0)
        g.add_edge(row["facility_id_from"], row["facility_id_to"], weight=weight, travel_time_min=row["travel_time_min"])

    # Normalize outgoing weights per node so SUM_j w_ij = 1 -- makes the
    # diffusion term a weighted average of neighbor stress, not an
    # unbounded sum that grows with how many real neighbors a facility has.
    for node in g.nodes:
        total = sum(data["weight"] for _, _, data in g.out_edges(node, data=True))
        if total > 0:
            for _, _, data in g.out_edges(node, data=True):
                data["norm_weight"] = data["weight"] / total

    return g


def propagate_stress(graph: nx.DiGraph, own_stress: dict[str, float], iterations: int = N_ITERATIONS) -> dict[str, float]:
    """Diffuse stress across the graph. own_stress: facility_id -> risk in [0,1]."""
    stress = dict(own_stress)
    for _ in range(iterations):
        next_stress = {}
        for node in graph.nodes:
            base = own_stress.get(node, 0.0)
            neighbor_contrib = sum(
                data["norm_weight"] * stress.get(target, 0.0) for _, target, data in graph.out_edges(node, data=True)
            )
            next_stress[node] = min(1.0, base + DELTA * neighbor_contrib)
        stress = next_stress
    return stress


def top_propagation_paths(graph: nx.DiGraph, source: str, own_stress: dict[str, float], k: int = 5) -> list[dict]:
    """Rank source's neighbors by propagation strength (w_ij), for the 'why' explainability panel."""
    edges = []
    for _, target, data in graph.out_edges(source, data=True):
        edges.append({"to": target, "travel_time_min": data["travel_time_min"], "weight": data["weight"]})
    edges.sort(key=lambda e: -e["weight"])
    return edges[:k]
