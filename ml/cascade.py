"""
Spillover-cascade model (build guide Section 05):

    stress_i(t+1) = own_stress_i + delta * SUM_j w_ij * stress_j(t),   w_ij ~ 1/travel_time(i,j)

Graph built from real OSRM travel times (data/processed/travel_times.csv).
Edges only exist between facilities that share a district (the only pairs
OSRM was queried for), matching the guide's "facilities sharing a catchment"
framing.
"""
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TRAVEL_TIMES_PATH = ROOT / "data" / "processed" / "travel_times.csv"

DELTA = 0.35  # propagation decay coefficient
N_ITERATIONS = 3


def build_facility_graph() -> nx.DiGraph:
    df = pd.read_csv(TRAVEL_TIMES_PATH)
    g = nx.DiGraph()
    for _, row in df.iterrows():
        weight = 1.0 / max(row["travel_time_min"], 1.0)
        g.add_edge(row["facility_id_from"], row["facility_id_to"], weight=weight, travel_time_min=row["travel_time_min"])
    return g


def propagate_stress(graph: nx.DiGraph, own_stress: dict[str, float], iterations: int = N_ITERATIONS) -> dict[str, float]:
    """Diffuse stress across the graph. own_stress: facility_id -> risk in [0,1]."""
    stress = dict(own_stress)
    for _ in range(iterations):
        next_stress = {}
        for node in graph.nodes:
            base = own_stress.get(node, 0.0)
            neighbor_contrib = 0.0
            for _, target, data in graph.out_edges(node, data=True):
                neighbor_contrib += data["weight"] * stress.get(target, 0.0)
            for source, _, data in graph.in_edges(node, data=True):
                neighbor_contrib += data["weight"] * stress.get(source, 0.0)
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
