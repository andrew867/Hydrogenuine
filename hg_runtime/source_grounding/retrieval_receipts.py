"""Source retrieval receipts — append-only, source is not truth."""

from __future__ import annotations

import hashlib
import json

SCHEMA_VERSION = "source_receipt_v1"


def create_receipt(*, request_id: str, url: str, title: str = "",
                   retrieved_at: str = "", retrieval_method: str = "",
                   source_type: str = "", claims_extracted: list[str] | None = None,
                   claim_support_records: list[str] | None = None,
                   claim_contradiction_records: list[str] | None = None,
                   reliability_notes: str = "") -> dict:
    receipt = {
        "schema": SCHEMA_VERSION,
        "source_id": "",
        "request_id": request_id,
        "url": url,
        "title": title,
        "retrieved_at": retrieved_at,
        "retrieval_method": retrieval_method,
        "source_type": source_type,
        "claims_extracted": claims_extracted or [],
        "claim_support_records": claim_support_records or [],
        "claim_contradiction_records": claim_contradiction_records or [],
        "reliability_notes": reliability_notes,
        "source_treated_as_truth": False,
        "grants_authority": False,
        "grants_tool_permission": False,
        "external_effect_created": False,
    }
    raw = json.dumps(receipt, sort_keys=True)
    receipt["source_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return receipt


def validate_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if receipt.get("grants_authority"):
        errors.append("grants_authority must be False")
    if receipt.get("grants_tool_permission"):
        errors.append("grants_tool_permission must be False")
    if receipt.get("external_effect_created"):
        errors.append("external_effect_created must be False")
    return errors
