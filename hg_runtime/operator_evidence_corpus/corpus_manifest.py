"""OEC corpus manifest records."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.schemas import assert_neutral, neutral_flags, record_hash

FIXED_TIME = "2026-06-20T00:00:00Z"


def build_operator_evidence_corpus(*, corpus_id: str, manifest_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "operator_evidence_corpus_v1",
        "corpus_id": corpus_id,
        "manifest_id": manifest_id,
        "created_at": FIXED_TIME,
        "doctrine_note": "Evidence corpus is not truth.",
        **neutral_flags(),
    }
    record["corpus_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_corpus_manifest(
    *,
    manifest_id: str,
    source_paths: list[str],
    claim_ids: list[str],
    family_ids: list[str],
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "corpus_manifest_v1",
        "manifest_id": manifest_id,
        "explicit_source_paths": source_paths,
        "source_count": len(source_paths),
        "claim_ids": claim_ids,
        "claim_count": len(claim_ids),
        "family_ids": family_ids,
        "family_count": len(family_ids),
        "only_explicit_paths": True,
        "directory_crawling_enabled": False,
        "created_at": FIXED_TIME,
        "doctrine_note": "Fixture corpus is not the world.",
        **neutral_flags(),
    }
    record["manifest_hash"] = record_hash(record)
    assert_neutral(record)
    return record
