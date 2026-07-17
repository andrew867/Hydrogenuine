"""SQP-3 provenance node builders.

A provenance node is metadata describing a point in local-evidence lineage. A
node is not a truth claim, not authority, and not a proof. Nodes only record
*where* something came from, never *that it is correct*.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import (
    PROVENANCE_NODE_TYPES,
    SQPBoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_provenance_node(
    *,
    node_id: str,
    node_type: str,
    ref: str,
    source_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    if node_type not in PROVENANCE_NODE_TYPES:
        raise SQPBoundaryError(f"unknown_provenance_node_type:{node_type}")
    record = {
        "schema_version": "1",
        "record_type": "provenance_node_v1",
        "node_id": node_id,
        "node_type": node_type,
        "ref": ref,
        "source_id": source_id,
        "metadata": dict(metadata or {}),
        "built_at": FIXED_TIME,
        "doctrine_note": "Provenance is not authority. Lineage is not truth.",
        "provenance_treated_as_authority": False,
        "lineage_treated_as_truth": False,
        "node_is_proof": False,
        "node_authorizes_action": False,
        "node_authorizes_tools": False,
        "node_promotes_belief": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
