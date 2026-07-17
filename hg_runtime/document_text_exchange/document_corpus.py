"""DTX document exchange schema builders."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import assert_neutral, neutral_flags, record_hash


def build_safe_text_document_exchange(*, exchange_id: str, manifest_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "safe_text_document_exchange_v1",
        "exchange_id": exchange_id,
        "manifest_id": manifest_id,
        "document_exchange_treated_as_truth": False,
        "document_corpus_treated_as_world": False,
        "doctrine_note": "Document exchange is not truth.",
        **neutral_flags(),
    }
    record["exchange_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_dtx_document_fixture(
    *,
    fixture_id: str,
    family_id: str,
    path_ref: str,
    logical_key: str,
    media_type: str,
    extract_allowed: bool = True,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_document_fixture_v1",
        "fixture_id": fixture_id,
        "family_id": family_id,
        "path_ref": path_ref,
        "logical_key": logical_key,
        "media_type": media_type,
        "extract_allowed": extract_allowed,
        "filename_treated_as_source_identity": False,
        "doctrine_note": "Filename is not source identity.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_dtx_expected_outcome(*, outcome_id: str, fixture_id: str, family_id: str, outcome_type: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_expected_outcome_v1",
        "outcome_id": outcome_id,
        "fixture_id": fixture_id,
        "family_id": family_id,
        "outcome_type": outcome_type,
        "expected_outcome_treated_as_proof": False,
        "doctrine_note": "Expected outcome is not proof.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_dtx_extraction_exchange_record(
    *,
    exchange_record_id: str,
    fixture_id: str,
    extraction_receipt_id: str,
    content_hash: str,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_extraction_exchange_record_v1",
        "exchange_record_id": exchange_record_id,
        "fixture_id": fixture_id,
        "extraction_receipt_id": extraction_receipt_id,
        "content_hash": content_hash,
        "extracted_text_treated_as_truth": False,
        "extraction_receipt_treated_as_truth": False,
        "content_hash_treated_as_truth": False,
        "doctrine_note": "Extracted text is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_dtx_leb_bridge_record(*, bridge_id: str, fixture_id: str, adapter_record_id: str, source_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_leb_bridge_record_v1",
        "bridge_id": bridge_id,
        "fixture_id": fixture_id,
        "adapter_record_id": adapter_record_id,
        "source_id": source_id,
        "dib_adapter_treated_as_belief_promotion": False,
        "leb_receipt_treated_as_truth": False,
        "automatic_belief_promotion": False,
        "doctrine_note": "DIB adapter is not belief promotion.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_dtx_packet_exchange_record(*, packet_id: str, fixture_id: str, family_id: str, claim_text: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_packet_exchange_record_v1",
        "packet_id": packet_id,
        "fixture_id": fixture_id,
        "family_id": family_id,
        "claim_text": claim_text,
        "packet_treated_as_truth": False,
        "packet_exchange_is_approval": False,
        "doctrine_note": "Packet exchange is not approval.",
        **neutral_flags(),
    }
    record["packet_hash"] = record_hash(record)
    assert_neutral(record)
    return record
