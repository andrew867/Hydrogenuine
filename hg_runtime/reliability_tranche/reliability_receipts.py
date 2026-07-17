"""Reliability Tranche receipts -- snapshot receipts for pre-soak readiness
and post-run finalization.

A receipt is NOT authority. Promotion is NEVER allowed. Operator review is
ALWAYS required. Model output is NOT truth. Source is NOT truth. Model
consensus is NOT proof.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "reliability_tranche_receipt_v1"

_INVARIANTS = {
    "promotion_allowed": False,
    "operator_review_required": True,
    "external_effects": False,
    "model_output_treated_as_truth": False,
    "source_is_not_truth": True,
    "model_consensus_is_not_proof": True,
}

_VALID_MODES = ("pre_soak", "post_run", "dry_run")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _receipt_id(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def create_receipt(
    *,
    mode: str,
    run_id: str = "",
    proof_path: str = "",
    modules_checked: list[str] | None = None,
    quality_status: str = "",
    contradiction_status: str = "",
    evidence_graph_status: str = "",
    memory_quarantine_status: str = "",
    public_claim_status: str = "",
    operator_read_model_status: str = "",
    stop_panic_status: str = "clear",
    final_readiness_verdict: str = "",
) -> dict:
    """Create a reliability tranche receipt.

    mode must be one of: pre_soak, post_run, dry_run.

    The receipt is a data structure only. It does NOT grant authority,
    does NOT promote to knowledge, and does NOT treat model output as truth.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: {_VALID_MODES}"
        )

    receipt = {
        "schema": SCHEMA_VERSION,
        "mode": mode,
        "run_id": run_id,
        "proof_path": proof_path,
        "modules_checked": list(modules_checked) if modules_checked else [],
        "quality_status": quality_status,
        "contradiction_status": contradiction_status,
        "evidence_graph_status": evidence_graph_status,
        "memory_quarantine_status": memory_quarantine_status,
        "public_claim_status": public_claim_status,
        "operator_read_model_status": operator_read_model_status,
        "stop_panic_status": stop_panic_status,
        "final_readiness_verdict": final_readiness_verdict,
        "timestamp": _utc_now_iso(),
        **_INVARIANTS,
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return receipt


def validate_receipt(receipt: dict) -> list[str]:
    """Validate a reliability tranche receipt.

    Checks invariants, schema version, and mode.
    Returns list of error strings (empty = valid).
    """
    errors = []

    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, "
            f"got {receipt.get('schema')}"
        )

    mode = receipt.get("mode")
    if mode not in _VALID_MODES:
        errors.append(f"invalid mode: {mode}")

    for key, expected in _INVARIANTS.items():
        actual = receipt.get(key)
        if actual is not expected:
            errors.append(f"{key} must be {expected}, got {actual}")

    return errors
