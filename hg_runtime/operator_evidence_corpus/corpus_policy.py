"""OEC corpus boundary policy."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.schemas import (
    ALLOWED_EXTENSIONS,
    CORPUS_APPROVED_ROOT,
    DENIED_EXTENSIONS,
    assert_neutral,
    neutral_flags,
    record_hash,
)

MAX_BYTES = 16_384


def build_corpus_boundary_policy(*, enabled: bool = True) -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "corpus_boundary_policy_v1",
        "policy_id": "oec-corpus-boundary-policy",
        "corpus_enabled": enabled,
        "explicit_manifest_required": True,
        "approved_root": CORPUS_APPROVED_ROOT,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "denied_extensions": list(DENIED_EXTENSIONS),
        "max_bytes": MAX_BYTES,
        "directory_crawling_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        "arbitrary_path_access_enabled": False,
        "pdf_ingestion_enabled": False,
        "binary_ingestion_enabled": False,
        "symlink_following_enabled": False,
        "links_followed": False,
        "web_access_enabled": False,
        "provider_access_enabled": False,
        "doctrine_note": "Corpus expansion is not arbitrary ingestion.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
