"""Evidence Graph receipts — snapshot and validation.

A receipt is a read-only snapshot of graph state at a point in time.
It does not confer authority. Promotion is NEVER allowed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone

from .graph_schema import _INVARIANTS


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_graph_receipt(graph: dict) -> dict:
    """Create a snapshot receipt of the current graph state.

    Counts nodes by type, edges, unsupported claims, contradictions,
    evidence gaps, and promotion decisions. All invariants are included.
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Count unsupported claims: claim nodes with no inbound
    # "claim_supported_by_source_candidate" edges
    claim_node_ids = {
        n["node_id"] for n in nodes if n.get("node_type") == "claim"
    }
    supported_ids = set()
    for e in edges:
        if e.get("edge_type") == "claim_supported_by_source_candidate":
            supported_ids.add(e.get("target_id"))
    unsupported_claims = len(claim_node_ids - supported_ids)

    # Count contradictions (contradiction nodes)
    contradiction_count = sum(
        1 for n in nodes if n.get("node_type") == "contradiction"
    )

    # Count evidence gaps
    evidence_gap_count = sum(
        1 for n in nodes if n.get("node_type") == "evidence_gap"
    )

    # Count promotion decisions
    promotion_decisions = sum(
        1 for n in nodes if n.get("node_type") == "promotion_decision"
    )

    receipt_data = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "unsupported_claims": unsupported_claims,
        "contradiction_count": contradiction_count,
        "evidence_gap_count": evidence_gap_count,
        "promotion_decisions": promotion_decisions,
        **copy.deepcopy(_INVARIANTS),
        "timestamp": _utc_now_iso(),
    }

    # Generate receipt_id from deterministic hash of counts
    hash_input = json.dumps(
        {
            "node_count": receipt_data["node_count"],
            "edge_count": receipt_data["edge_count"],
            "unsupported_claims": receipt_data["unsupported_claims"],
            "contradiction_count": receipt_data["contradiction_count"],
            "evidence_gap_count": receipt_data["evidence_gap_count"],
            "promotion_decisions": receipt_data["promotion_decisions"],
        },
        sort_keys=True,
    )
    receipt_data["receipt_id"] = hashlib.sha256(
        hash_input.encode("utf-8")
    ).hexdigest()[:16]

    return receipt_data


def validate_graph_receipt(receipt: dict) -> list[str]:
    """Validate all invariants in a graph receipt.

    Returns list of errors (empty = valid).
    """
    errors = []

    for key, expected in _INVARIANTS.items():
        actual = receipt.get(key)
        if actual is not expected:
            errors.append(
                f"{key} must be {expected}, got {actual}"
            )

    return errors
