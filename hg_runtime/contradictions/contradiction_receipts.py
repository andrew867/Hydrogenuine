"""Receipt factory for contradiction records.

Contradiction is not a truth decision. Model consensus is not proof.
promotion_allowed is always False. operator_review_required is always True.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from hg_runtime.contradictions.contradiction_types import (
    CONTRADICTION_TYPES,
    SEVERITY_LEVELS,
    RESOLUTION_STATES,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _contradiction_id(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def create_contradiction_receipt(
    *,
    contradiction_type: str,
    claim_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    model_ids: list[str] | None = None,
    persona_lens_ids: list[str] | None = None,
    summary: str,
    severity: str = "medium",
    run_id: str = "",
    review_id: str = "",
) -> dict:
    """Create a contradiction receipt.

    Contradictions are NOT resolved to truth by the system.
    Operator review is ALWAYS required. Promotion is NEVER allowed.
    """
    receipt = {
        "schema": "contradiction_receipt_v2",
        "contradiction_id": "",
        "run_id": run_id,
        "review_id": review_id,
        "claim_ids": list(claim_ids) if claim_ids else [],
        "source_ids": list(source_ids) if source_ids else [],
        "model_ids": list(model_ids) if model_ids else [],
        "persona_lens_ids": list(persona_lens_ids) if persona_lens_ids else [],
        "contradiction_type": contradiction_type,
        "summary": summary,
        "supporting_receipts": [],
        "severity": severity,
        "resolution_state": "unresolved",
        "promotion_allowed": False,
        "operator_review_required": True,
        "model_consensus_is_not_proof": True,
        "contradiction_resolved_to_truth": False,
        "grants_authority": False,
        "model_output_treated_as_truth": False,
        "created_at": _utc_now_iso(),
    }
    receipt["contradiction_id"] = _contradiction_id(receipt)
    return receipt


def validate_contradiction_receipt(receipt: dict) -> list[str]:
    """Validate a contradiction receipt. Returns list of errors (empty = valid)."""
    errors = []

    if receipt.get("schema") != "contradiction_receipt_v2":
        errors.append(f"wrong schema: {receipt.get('schema')}")

    ct = receipt.get("contradiction_type")
    if ct not in CONTRADICTION_TYPES:
        errors.append(f"unknown contradiction_type: {ct}")

    sev = receipt.get("severity")
    if sev not in SEVERITY_LEVELS:
        errors.append(f"unknown severity: {sev}")

    rs = receipt.get("resolution_state")
    if rs not in RESOLUTION_STATES:
        errors.append(f"unknown resolution_state: {rs}")

    if receipt.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")
    if receipt.get("operator_review_required") is not True:
        errors.append("operator_review_required must be True")
    if receipt.get("model_consensus_is_not_proof") is not True:
        errors.append("model_consensus_is_not_proof must be True")
    if receipt.get("contradiction_resolved_to_truth") is not False:
        errors.append("contradiction_resolved_to_truth must be False")
    if receipt.get("grants_authority") is not False:
        errors.append("grants_authority must be False")
    if receipt.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    if not receipt.get("summary"):
        errors.append("missing summary")

    return errors
