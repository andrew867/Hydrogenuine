"""OES soak boundary policy."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import assert_neutral, neutral_flags, record_hash

FIXED_TIME = "2026-06-20T00:00:00Z"


def build_soak_policy(*, iteration_count: int = 5) -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "soak_policy_v1",
        "policy_id": "oes-soak-policy-v1",
        "iteration_count": iteration_count,
        "explicit_corpus_manifest_only": True,
        "directory_crawling_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "web_access_enabled": False,
        "provider_access_enabled": False,
        "mutation_auto_repair_enabled": False,
        "deletion_enabled": False,
        "doctrine_note": "Soak is not proof of truth.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy


def build_operator_evidence_soak(*, soak_id: str, manifest_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "operator_evidence_soak_v1",
        "soak_id": soak_id,
        "manifest_id": manifest_id,
        "created_at": FIXED_TIME,
        "doctrine_note": "Soak is not proof of truth.",
        **neutral_flags(),
    }
    record["soak_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_soak_manifest(*, manifest_id: str, corpus_manifest_ref: str, iteration_count: int) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "soak_manifest_v1",
        "manifest_id": manifest_id,
        "corpus_manifest_ref": corpus_manifest_ref,
        "iteration_count": iteration_count,
        "explicit_corpus_manifest_only": True,
        "old_proof_mutated": False,
        **neutral_flags(),
    }
    record["manifest_hash"] = record_hash(record)
    assert_neutral(record)
    return record
