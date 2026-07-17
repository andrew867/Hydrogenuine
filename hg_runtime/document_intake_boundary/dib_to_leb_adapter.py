"""DIB-3 DIB to LEB adapter records (no belief promotion)."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_dib_to_leb_adapter_record(
    *,
    adapter_id: str,
    source_id: str,
    extraction_receipt_id: str,
    content_hash: str,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dib_to_leb_adapter_record_v1",
        "adapter_id": adapter_id,
        "source_id": source_id,
        "extraction_receipt_id": extraction_receipt_id,
        "content_hash": content_hash,
        "leb_adapter_is_belief_promotion": False,
        "automatic_belief_promotion": False,
        "evidence_receipt_is_truth": False,
        "evidence_receipt_is_authority": False,
        "extracted_text_treated_as_truth": False,
        "doctrine_note": "LEB adapter record is not belief promotion.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
