"""LEB-0 source identity records."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.evidence_boundary import validate_source_path
from hg_runtime.local_evidence_bridge.schemas import assert_neutral, neutral_flags, record_hash


def build_operator_source(*, source_id: str, source_path: str, declared_by: str = "operator_fixture") -> dict:
    validate_source_path(source_path)
    source = {
        "schema_version": "1",
        "record_type": "operator_provided_source_v1",
        "source_id": source_id,
        "source_path": source_path,
        "declared_by": declared_by,
        "operator_provided_source_is_truth": False,
        "local_file_trusted_by_default": False,
        "approved_fixture_path": True,
        **neutral_flags(),
    }
    source["record_hash"] = record_hash(source)
    assert_neutral(source)
    return source
