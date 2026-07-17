"""P26 read-only recall index."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.ledger_adapter import build_p26_1_ledger
from hg_runtime.experience_ledger.schemas import assert_neutral


def build_recall_index(repo_root) -> dict:
    layer = build_p26_1_ledger(repo_root)
    by_memory = {record["memory_id"]: record for record in layer["memory_records"]}
    by_experience = {record["experience_id"]: record for record in layer["experience_records"]}
    entries = []
    for memory in layer["memory_records"]:
        experience = by_experience[memory["experience_id"]]
        entry = {
            "record_type": "recall_index_entry_v1",
            "schema_version": "1",
            "memory_id": memory["memory_id"],
            "memory_hash": memory["memory_hash"],
            "experience_id": memory["experience_id"],
            "family": memory["family"],
            "artifact_ref": memory["artifact_ref"],
            "artifact_id": memory["memory_id"].removeprefix("mem-"),
            "verdict": experience["verdict"],
            "boundary_tags": experience["boundary_tags"],
            "risk_tags": experience["boundary_tags"],
            "provenance_refs": memory["provenance_refs"],
            "source_quality_refs": memory["source_quality_refs"],
            "time_window": "ALL_FIXTURE_TIME",
            "retraction_status": "ACTIVE",
            "quarantine_status": "CLEAR",
            "read_only": True,
            "memory_treated_as_truth": False,
            "recall_treated_as_authority": False,
            "tools_authorized": False,
            "belief_promoted": False,
            "deletion_performed": False,
        }
        with_hash(entry, "record_hash")
        assert_neutral(entry)
        entries.append(entry)
    index = {
        "record_type": "recall_index_v1",
        "schema_version": "1",
        "index_id": "p26-2-read-only-recall-index",
        "entry_count": len(entries),
        "entries": entries,
        "read_only": True,
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
        "authority_granted": False,
        "tools_authorized": False,
    }
    with_hash(index, "manifest_hash")
    assert_neutral(index)
    return {"index": index, "entries": entries, "memory_records": list(by_memory.values())}

