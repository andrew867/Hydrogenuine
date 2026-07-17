"""P27 skill edge builders."""

from __future__ import annotations

from hg_runtime.skill_graph.hashing import with_hash
from hg_runtime.skill_graph.p27_schemas import assert_neutral, neutral_flags


def build_skill_edge(
    *,
    edge_id: str,
    source_skill_id: str,
    target_skill_id: str,
    edge_type: str,
    evidence_refs: list[str],
) -> dict:
    record = {
        "record_type": "skill_edge_v1",
        "schema_version": "1",
        "edge_id": edge_id,
        "source_skill_id": source_skill_id,
        "target_skill_id": target_skill_id,
        "edge_type": edge_type,
        "evidence_refs": list(evidence_refs),
        "edge_is_not_transfer_proof": True,
        **neutral_flags(),
    }
    with_hash(record, "edge_hash")
    assert_neutral(record)
    return record
