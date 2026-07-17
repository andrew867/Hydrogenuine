"""SQP-3 provenance edge builders.

A provenance edge is a directed lineage link between two nodes. A path through
the graph is not a proof, and the existence of an edge never grants authority,
authorizes action, or promotes belief. A ``DUPLICATE_OF`` edge in particular is
*not* corroboration: duplicate copies are not independent sources.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import (
    PROVENANCE_EDGE_TYPES,
    SQPBoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_provenance_edge(
    *,
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    edge_type: str,
    evidence_ref: str,
) -> dict:
    if edge_type not in PROVENANCE_EDGE_TYPES:
        raise SQPBoundaryError(f"unknown_provenance_edge_type:{edge_type}")
    record = {
        "schema_version": "1",
        "record_type": "provenance_edge_v1",
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "edge_type": edge_type,
        "evidence_ref": evidence_ref,
        "built_at": FIXED_TIME,
        "doctrine_note": "A provenance path is not proof. A duplicate is not corroboration.",
        "provenance_treated_as_authority": False,
        "lineage_treated_as_truth": False,
        "edge_is_proof": False,
        "duplicate_treated_as_corroboration": False,
        "edge_authorizes_action": False,
        "edge_promotes_belief": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
