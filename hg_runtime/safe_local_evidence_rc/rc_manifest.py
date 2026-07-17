"""SLE-RC manifest builders."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import (
    COMPONENT_FAMILIES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_safe_local_evidence_rc(*, rc_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "safe_local_evidence_rc_v1",
        "rc_id": rc_id,
        "provider_mode": PROVIDER_MODE,
        "local_only": True,
        "fixture_only": True,
        "component_families": list(COMPONENT_FAMILIES),
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "doctrine_note": "Release candidate is not production deployment.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_rc_manifest(*, manifest_id: str, component_count: int) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_manifest_v1",
        "manifest_id": manifest_id,
        "provider_mode": PROVIDER_MODE,
        "component_family_count": component_count,
        "component_families": list(COMPONENT_FAMILIES),
        "safe_text_markdown_only": True,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        "html_parsing_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "doctrine_note": "RC GREEN is not truth, authority, or live permission.",
        **neutral_flags(),
    }
    record["manifest_hash"] = record_hash(record)
    assert_neutral(record)
    return record
