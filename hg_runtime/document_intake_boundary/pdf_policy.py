"""DIB-4 PDF disabled policy."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_pdf_disabled_policy(*, policy_id: str = "dib-pdf-disabled-policy-v1") -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "pdf_disabled_policy_v1",
        "policy_id": policy_id,
        "pdf_ingestion_enabled": False,
        "pdf_text_extraction_enabled": False,
        "pdf_parser_dependency_allowed": False,
        "pdf_metadata_treated_as_provenance": False,
        "pdf_filename_treated_as_source_identity": False,
        "doctrine_note": "PDF ingestion and text extraction remain disabled.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
