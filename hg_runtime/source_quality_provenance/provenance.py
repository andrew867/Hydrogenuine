"""Provenance schema records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_provenance_node(*, node_id: str, node_type: str, ref: str, source_id: str | None = None) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "provenance_node_v1",
        "node_id": node_id,
        "node_type": node_type,
        "ref": ref,
        "source_id": source_id,
        "metadata": {"phase19_verdict": "YELLOW_PRESERVED"} if source_id == "sqp-source-phase19" else {},
        "provenance_treated_as_authority": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_provenance_edge(*, edge_id: str, from_node_id: str, to_node_id: str, edge_type: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "provenance_edge_v1",
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "edge_type": edge_type,
        "evidence_ref": "schema-foundation-fixture",
        "provenance_treated_as_authority": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_provenance_graph(*, graph_id: str, source_ids: list[str], nodes: list[dict], edges: list[dict]) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "provenance_graph_v1",
        "graph_id": graph_id,
        "source_ids": source_ids,
        "distinct_source_count": len(set(source_ids)),
        "nodes": [node["record_hash"] for node in nodes],
        "edges": [edge["record_hash"] for edge in edges],
        "built_at": FIXED_TIME,
        "doctrine_note": "Provenance is not authority.",
        "provenance_treated_as_authority": False,
        **neutral_flags(),
    }
    record["graph_hash"] = record_hash(record)
    assert_neutral(record)
    return record
