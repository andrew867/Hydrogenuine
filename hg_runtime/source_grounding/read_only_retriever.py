"""Read-only source retrieval queue.

Source is not truth. Browser result is not truth. Retrieved text is not
knowledge. This module never performs login, registration, posting, form
submission, payment, comment, upload, or any external side effect.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "source_retrieval_queue_v1"

FORBIDDEN_ACTIONS = frozenset({
    "login", "registration", "posting", "form_submit",
    "comment", "message", "upload", "payment", "purchase",
    "api_key_discovery", "scraping_bypass", "paywall_bypass",
    "social_media_interaction", "email", "publication",
})

ALLOWED_RETRIEVAL_METHODS = frozenset({
    "browser_read_only", "mcp_read_only", "operator_paste",
    "fixture", "cached",
})


def create_source_candidate(*, url: str, seed_ids: list[str] | None = None,
                            source_type: str = "unknown",
                            operator_notes: str = "",
                            priority: str = "medium") -> dict:
    candidate = {
        "schema": SCHEMA_VERSION,
        "source_candidate_id": "",
        "url": url,
        "seed_ids": seed_ids or [],
        "source_type": source_type,
        "operator_notes": operator_notes,
        "priority": priority,
        "status": "queued",
        "retrieval_receipt_id": "",
        "source_treated_as_truth": False,
        "grants_authority": False,
        "external_effect_authorized": False,
    }
    raw = json.dumps(candidate, sort_keys=True)
    candidate["source_candidate_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return candidate


def create_retrieval_receipt(*, source_candidate_id: str, url: str,
                            title: str = "", content_text: str = "",
                            retrieval_method: str = "browser_read_only",
                            source_type: str = "unknown",
                            success: bool = True,
                            failure_reason: str = "",
                            safety_notes: str = "",
                            redacted_fields: list[str] | None = None) -> dict:
    if retrieval_method not in ALLOWED_RETRIEVAL_METHODS:
        raise ValueError(f"retrieval method {retrieval_method!r} not in allowed set")

    content_hash = hashlib.sha256(content_text.encode()).hexdigest() if content_text else ""

    receipt = {
        "schema": "source_retrieval_receipt_v1",
        "retrieval_receipt_id": "",
        "source_candidate_id": source_candidate_id,
        "url": url,
        "title": title,
        "content_hash": content_hash,
        "content_length": len(content_text),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_method": retrieval_method,
        "source_type": source_type,
        "success": success,
        "failure_reason": failure_reason,
        "safety_notes": safety_notes,
        "redacted_fields": redacted_fields or [],
        "read_only_policy_enforced": True,
        "no_login": True,
        "no_registration": True,
        "no_posting": True,
        "no_form_submit": True,
        "no_payment": True,
        "no_upload": True,
        "no_comment": True,
        "no_message": True,
        "no_publication": True,
        "source_treated_as_truth": False,
        "grants_authority": False,
        "external_effect_created": False,
        "promotion_decision": "reject_pending_gate",
    }
    raw = json.dumps(receipt, sort_keys=True)
    receipt["retrieval_receipt_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return receipt


def create_failure_receipt(*, source_candidate_id: str, url: str,
                          failure_reason: str,
                          retrieval_method: str = "browser_read_only") -> dict:
    return create_retrieval_receipt(
        source_candidate_id=source_candidate_id,
        url=url,
        retrieval_method=retrieval_method,
        success=False,
        failure_reason=failure_reason,
    )


def validate_retrieval_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != "source_retrieval_receipt_v1":
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if receipt.get("grants_authority"):
        errors.append("grants_authority must be False")
    if receipt.get("external_effect_created"):
        errors.append("external_effect_created must be False")
    if not receipt.get("read_only_policy_enforced"):
        errors.append("read_only_policy_enforced must be True")
    for flag in ["no_login", "no_registration", "no_posting",
                 "no_form_submit", "no_payment", "no_upload",
                 "no_comment", "no_message", "no_publication"]:
        if not receipt.get(flag, False):
            errors.append(f"{flag} must be True")
    if receipt.get("retrieval_method") not in ALLOWED_RETRIEVAL_METHODS:
        errors.append(f"disallowed retrieval_method: {receipt.get('retrieval_method')}")
    return errors


def check_action_forbidden(action: str) -> bool:
    return action.lower().replace(" ", "_").replace("-", "_") in FORBIDDEN_ACTIONS
