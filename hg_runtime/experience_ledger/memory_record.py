"""P26 memory record builders."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.schemas import assert_neutral, neutral_flags


def build_memory_record(
    *,
    memory_id: str,
    experience_record: dict,
    provenance_refs: list[str],
    source_quality_refs: list[str] | None = None,
    retraction_supported: bool = True,
    quarantine_supported: bool = True,
) -> dict:
    record = {
        "record_type": "memory_record_v1",
        "schema_version": "1",
        "memory_id": memory_id,
        "experience_id": experience_record["experience_id"],
        "experience_hash": experience_record["experience_hash"],
        "family": experience_record["family"],
        "artifact_ref": experience_record["artifact_ref"],
        "provenance_refs": list(provenance_refs),
        "source_quality_refs": list(source_quality_refs or []),
        "retraction_supported": retraction_supported,
        "quarantine_supported": quarantine_supported,
        "memory_is_truth": False,
        "memory_treated_as_truth": False,
        "ledger_entry_treated_as_belief": False,
        **neutral_flags(),
    }
    with_hash(record, "memory_hash")
    assert_neutral(record)
    return record

