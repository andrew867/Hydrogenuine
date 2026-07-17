"""P26 experience record builders."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.schemas import assert_neutral, neutral_flags


def build_experience_record(
    *,
    experience_id: str,
    family: str,
    artifact_ref: str,
    verdict: str,
    boundary_tags: list[str],
    provenance_refs: list[str],
) -> dict:
    record = {
        "record_type": "experience_record_v1",
        "schema_version": "1",
        "experience_id": experience_id,
        "family": family,
        "artifact_ref": artifact_ref,
        "verdict": verdict,
        "boundary_tags": list(boundary_tags),
        "provenance_refs": list(provenance_refs),
        "experience_is_evidence_by_itself": False,
        "ledger_entry_is_belief": False,
        **neutral_flags(),
    }
    with_hash(record, "experience_hash")
    assert_neutral(record)
    return record

