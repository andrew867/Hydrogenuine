"""Model inference receipts for source-grounded soak cycles.

Model output is not truth. Model confidence is not proof.
Model consensus is not proof. No promotion. Operator review required.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "model_inference_receipt_v1"


def create_model_inference_receipt(
    *,
    run_id: str = "",
    cycle_id: str = "",
    source_candidate_id: str = "",
    source_receipt_id: str = "",
    model_route_receipt_id: str = "",
    persona_lens_id: str = "",
    model_provider: str = "",
    model_name: str = "",
    endpoint_kind: str = "unavailable",
    endpoint_url_redacted: str = "",
    remote_fallback_used: bool = False,
    request_started_at: str = "",
    request_completed_at: str = "",
    latency_ms: int = 0,
    prompt_hash: str = "",
    source_text_hash: str = "",
    source_text_extract_path: str = "",
    source_text_chars_used: int = 0,
    max_source_chars: int = 0,
    output_hash: str = "",
    output_text_path: str = "",
    output_chars: int = 0,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    finish_reason: str = "",
    inference_status: str = "success",
    error_type: str = "",
    error_message: str = "",
    notes: str = "",
) -> dict:
    receipt = {
        "schema": SCHEMA_VERSION,
        "receipt_id": "",
        "run_id": run_id,
        "cycle_id": cycle_id,
        "source_candidate_id": source_candidate_id,
        "source_receipt_id": source_receipt_id,
        "model_route_receipt_id": model_route_receipt_id,
        "persona_lens_id": persona_lens_id,
        "model_provider": model_provider,
        "model_name": model_name,
        "endpoint_kind": endpoint_kind,
        "endpoint_url_redacted": endpoint_url_redacted,
        "remote_fallback_used": remote_fallback_used,
        "request_started_at": request_started_at,
        "request_completed_at": request_completed_at,
        "latency_ms": latency_ms,
        "prompt_hash": prompt_hash,
        "source_text_hash": source_text_hash,
        "source_text_extract_path": source_text_extract_path,
        "source_text_chars_used": source_text_chars_used,
        "max_source_chars": max_source_chars,
        "output_hash": output_hash,
        "output_text_path": output_text_path,
        "output_chars": output_chars,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "finish_reason": finish_reason,
        "model_output_is_truth": False,
        "model_confidence_is_proof": False,
        "model_consensus_is_proof": False,
        "promotion_allowed": False,
        "operator_review_required": True,
        "stop_panic_checked": True,
        "inference_status": inference_status,
        "error_type": error_type,
        "error_message": error_message,
        "notes": notes,
    }
    raw = json.dumps(receipt, sort_keys=True)
    receipt["receipt_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return receipt


def validate_model_inference_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("model_output_is_truth") is not False:
        errors.append("model_output_is_truth must be False")
    if receipt.get("model_confidence_is_proof") is not False:
        errors.append("model_confidence_is_proof must be False")
    if receipt.get("model_consensus_is_proof") is not False:
        errors.append("model_consensus_is_proof must be False")
    if receipt.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")
    if receipt.get("operator_review_required") is not True:
        errors.append("operator_review_required must be True")
    if receipt.get("remote_fallback_used") is True:
        errors.append("remote_fallback_used must be False for local-only")
    valid_statuses = {
        "success", "skipped_dry_run", "skipped_no_source_text",
        "provider_unavailable", "timeout", "malformed", "error", "stopped",
    }
    status = receipt.get("inference_status", "")
    if status not in valid_statuses:
        errors.append(f"invalid inference_status: {status}")
    return errors
