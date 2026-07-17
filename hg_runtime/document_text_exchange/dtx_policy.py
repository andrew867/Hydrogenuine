"""DTX boundary policy."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import DTX_APPROVED_ROOT, PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_dtx_boundary_policy(*, policy_id: str = "dtx-boundary-policy-v1") -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "dtx_boundary_policy_v1",
        "policy_id": policy_id,
        "approved_root": DTX_APPROVED_ROOT,
        "allowed_extensions": [".txt", ".md"],
        "manifest_extensions": [".json"],
        "explicit_manifest_only": True,
        "arbitrary_file_ingestion_enabled": False,
        "directory_crawling_enabled": False,
        "symlink_following_enabled": False,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        "html_parsing_enabled": False,
        "web_fetch_enabled": False,
        "external_provider_enabled": False,
        "automatic_belief_promotion_enabled": False,
        "deletion_enabled": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "doctrine_note": "Document exchange is not truth.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
