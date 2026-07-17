"""
OS Post-Phase 5: Impact graph and blast radius.
"""

from .build_graph import (
    build_impact_graph,
    get_dependency_closure,
    compute_blast_radius,
    record_impact_edge,
)

__all__ = [
    "build_impact_graph",
    "get_dependency_closure",
    "compute_blast_radius",
    "record_impact_edge",
]
