"""LEB-0 evidence receipt builders."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import assert_neutral, neutral_flags, record_hash


def build_evidence_receipt(*, receipt_id: str, source_id: str, source_hash: str) -> dict:
    receipt = {
        "schema_version": "1",
        "record_type": "local_evidence_receipt_v1",
        "receipt_id": receipt_id,
        "source_id": source_id,
        "source_hash": source_hash,
        "evidence_receipt_is_truth": False,
        "evidence_receipt_is_authority": False,
        "automatic_belief_promotion": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = record_hash(receipt)
    assert_neutral(receipt)
    return receipt


def build_excerpt_receipt(*, excerpt_id: str, source_id: str, excerpt_hash: str) -> dict:
    receipt = {
        "schema_version": "1",
        "record_type": "source_excerpt_receipt_v1",
        "excerpt_id": excerpt_id,
        "source_id": source_id,
        "excerpt_hash": excerpt_hash,
        "source_excerpt_is_belief": False,
        "automatic_belief_promotion": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = record_hash(receipt)
    assert_neutral(receipt)
    return receipt


def build_boundary_receipt(*, boundary_id: str) -> dict:
    receipt = {
        "schema_version": "1",
        "record_type": "evidence_boundary_receipt_v1",
        "boundary_id": boundary_id,
        "operator_provided_source_is_truth": False,
        "local_file_trusted_by_default": False,
        "source_excerpt_is_belief": False,
        "evidence_receipt_is_truth": False,
        "evidence_receipt_is_authority": False,
        "request_is_permission": False,
        "ais_record_health_can_scan_later": True,
        "quarantine_can_isolate_suspect_sources_later": True,
        "fever_can_restrict_ingestion_later": True,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = record_hash(receipt)
    assert_neutral(receipt)
    return receipt
