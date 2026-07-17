"""Integration receipt pipeline — source is not truth.

Ties together: web receipt + claim extraction + boundary audit + promotion
guard.  Every sub-result carries its own safety invariants.  The pipeline
result adds a top-level invariant block that must remain all-False/False.

Source is not truth.  Model output is not truth.  No promotion without
operator + gate.  No external effects.  No tool authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from .read_only_web_retriever import create_web_receipt, validate_web_receipt
from .source_claim_extractor import extract_classified_claims, validate_extraction
from .speculative_boundary_audit import audit_seed_claims, validate_audit
from .source_promotion_guard import evaluate_promotion, validate_promotion_decision

SCHEMA_VERSION = "source_receipt_pipeline_v1"

_INVARIANTS = {
    "source_treated_as_truth": False,
    "promotion_allowed": False,
    "external_effects_attempted": False,
    "tool_authority_granted": False,
    "model_output_treated_as_truth": False,
}


def _blocked_result(source_candidate_id: str, url: str, run_id: str) -> dict:
    """Return a fully-blocked pipeline result (stop/panic mode)."""
    return {
        "schema": SCHEMA_VERSION,
        "pipeline_id": "",
        "source_candidate_id": source_candidate_id,
        "url": url,
        "run_id": run_id,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "blocked": True,
        "block_reason": "stop_panic",
        "web_receipt": {},
        "claim_extraction": {},
        "boundary_audit": {},
        "promotion_decision": {
            "promotion_allowed": False,
            "decision": "reject",
            "rejection_reasons": ["stop_panic"],
            "operator_approved": False,
            "gate_passed": False,
            "source_treated_as_truth": False,
            "model_output_treated_as_truth": False,
        },
        **_INVARIANTS,
    }


def process_source(
    *,
    source_candidate_id: str,
    url: str,
    content_text: str = "",
    title: str = "",
    http_status: int = 200,
    content_type: str = "text/html",
    fetch_method: str = "GET",
    retrieval_method: str = "direct_url",
    access_status: str = "public",
    screenshot_hashes: list[str] | None = None,
    screenshot_paths: list[str] | None = None,
    run_id: str = "",
    stop_panic: bool = False,
) -> dict:
    """Full pipeline: web receipt -> claim extraction -> boundary audit -> promotion guard."""
    if stop_panic:
        return _blocked_result(source_candidate_id, url, run_id)

    # 1. Create web receipt
    web_receipt = create_web_receipt(
        source_candidate_id=source_candidate_id,
        url=url,
        fetch_method=fetch_method,
        http_status=http_status,
        content_type=content_type,
        title=title,
        access_status=access_status,
        content_text=content_text,
        screenshot_hashes=screenshot_hashes,
        screenshot_paths=screenshot_paths,
        retrieval_method=retrieval_method,
    )

    # 2. Extract classified claims
    claim_extraction = extract_classified_claims(
        content_text,
        source_receipt_id=web_receipt.get("receipt_id", ""),
    )

    # 3. Run boundary audit on direct + inferred claims
    all_claims = (
        claim_extraction.get("direct_claims", [])
        + claim_extraction.get("inferred_claims", [])
    )
    boundary_audit = audit_seed_claims(
        seed_id=source_candidate_id,
        claims=all_claims,
        source_receipt_id=web_receipt.get("receipt_id", ""),
    )

    # 4. Evaluate promotion (no operator approval, no gate)
    promotion_decision = evaluate_promotion(
        source_receipt=web_receipt,
        boundary_audit=boundary_audit,
        operator_approved=False,
        gate_passed=False,
    )

    result = {
        "schema": SCHEMA_VERSION,
        "pipeline_id": "",
        "source_candidate_id": source_candidate_id,
        "url": url,
        "run_id": run_id,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "blocked": False,
        "block_reason": "",
        "web_receipt": web_receipt,
        "claim_extraction": claim_extraction,
        "boundary_audit": boundary_audit,
        "promotion_decision": promotion_decision,
        **_INVARIANTS,
    }
    raw = json.dumps(result, sort_keys=True)
    result["pipeline_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return result


def validate_pipeline_result(result: dict) -> list[str]:
    """Check all invariants hold on a pipeline result."""
    errors = []

    if result.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {result.get('schema')}")

    # Top-level invariants
    for key, expected in _INVARIANTS.items():
        if result.get(key) != expected:
            errors.append(f"invariant violated: {key} is {result.get(key)}, expected {expected}")

    # Sub-result validations (skip if blocked/empty)
    if result.get("web_receipt"):
        errors.extend(validate_web_receipt(result["web_receipt"]))

    if result.get("claim_extraction"):
        errors.extend(validate_extraction(result["claim_extraction"]))

    if result.get("boundary_audit"):
        errors.extend(validate_audit(result["boundary_audit"]))

    if result.get("promotion_decision"):
        errors.extend(validate_promotion_decision(result["promotion_decision"]))

    return errors


def write_receipts_jsonl(results: list[dict], output_dir: str) -> dict:
    """Write pipeline results to JSONL files in output_dir.

    Creates:
      - source_receipts.jsonl   (one line per pipeline result)
      - source_claims.jsonl     (one line per claim extraction)
      - boundary_audits.jsonl   (one line per boundary audit)

    Returns dict with file paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    receipts_path = os.path.join(output_dir, "source_receipts.jsonl")
    claims_path = os.path.join(output_dir, "source_claims.jsonl")
    audits_path = os.path.join(output_dir, "boundary_audits.jsonl")

    with open(receipts_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    with open(claims_path, "w", encoding="utf-8") as f:
        for r in results:
            extraction = r.get("claim_extraction")
            if extraction:
                f.write(json.dumps(extraction, sort_keys=True) + "\n")

    with open(audits_path, "w", encoding="utf-8") as f:
        for r in results:
            audit = r.get("boundary_audit")
            if audit:
                f.write(json.dumps(audit, sort_keys=True) + "\n")

    return {
        "source_receipts": receipts_path,
        "source_claims": claims_path,
        "boundary_audits": audits_path,
    }
