"""P30 acquisition source record builder."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import assert_neutral, neutral_flags


def build_acquisition_source_record(
    *,
    source_id: str,
    source_type: str,
    artifact_path: str,
    provenance_refs: list[str],
    quality_score: str | None = None,
) -> dict:
    record = {
        "record_type": "acquisition_source_record_v1",
        "schema_version": "1",
        "source_id": source_id,
        "source_type": source_type,
        "artifact_path": artifact_path,
        "provenance_refs": list(provenance_refs),
        "quality_score": quality_score,
        "source_is_not_authority": True,
        "source_quality_is_not_truth": True,
        "provenance_is_not_authority": True,
        "doctrine_note": "Source is not authority. Source quality is not truth.",
        **neutral_flags(),
    }
    with_hash(record, "source_hash")
    assert_neutral(record)
    return record
