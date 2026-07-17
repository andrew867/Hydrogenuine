"""Causal edges and the correlation/causation boundary.

An edge is a hypothesized relation, never truth. Correlation-only edges use the
CORRELATES_WITH relation and must never be promoted to causation: any attempt to
set correlation_is_causation true is rejected.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    CAUSAL_EDGE_RECORD_SCHEMA,
    CausalBoundaryError,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

# Map a hypothesis scenario to a relation type for HYPOTHETICAL edges.
SCENARIO_RELATION = {
    "CAUSAL": "CAUSES_HYPOTHESIZED",
    "CORRELATION": "CORRELATES_WITH",
    "MECHANISM": "MECHANISM_PROPOSED",
    "PREDICTION": "ENABLES_HYPOTHESIZED",
}

_STATUS_BY_HYPOTHESIS = {
    "PROPOSED": "HYPOTHETICAL",
    "CONTRADICTED": "CONTRADICTED",
    "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
}


def build_causal_edge(*, hypothesis: dict, scenario: str) -> dict:
    claim_id = hypothesis["hypothesis_id"].replace("hyp-", "", 1)
    relation = SCENARIO_RELATION.get(scenario, "CORRELATES_WITH")
    edge_status = _STATUS_BY_HYPOTHESIS.get(hypothesis["hypothesis_status"], "INSUFFICIENT_EVIDENCE")
    edge = {
        "schema": CAUSAL_EDGE_RECORD_SCHEMA,
        "edge_id": f"edge-{claim_id}",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "source_node_id": f"node-{claim_id}-cause",
        "target_node_id": f"node-{claim_id}-effect",
        "relation_type": relation,
        "edge_status": edge_status,
        "edge_is_truth": False,
        "correlation_is_causation": False,
        **neutral_flags(),
    }
    edge["edge_hash"] = canonical_hash(edge)
    return edge


def assert_correlation_not_causation(edge: dict) -> None:
    """Refuse to treat a correlation-only edge as causation."""
    if edge.get("correlation_is_causation") or edge.get("correlation_treated_as_causation"):
        raise CausalBoundaryError("correlation_treated_as_causation")
    if edge.get("relation_type") == "CORRELATES_WITH" and edge.get("edge_is_truth"):
        raise CausalBoundaryError("causal_edge_treated_as_truth")
