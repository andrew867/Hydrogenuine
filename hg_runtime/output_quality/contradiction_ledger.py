"""Contradiction Ledger — accumulate contradictions and agreements from
adjudication and model comparison.

Contradictions are NOT resolved to truth. Model consensus is NOT proof.
Promotion is NEVER allowed. Operator review is ALWAYS required for
contradictions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "contradiction_ledger_v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry_id(entry: dict) -> str:
    raw = json.dumps(entry, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def create_ledger() -> dict:
    """Create an empty contradiction ledger."""
    return {
        "schema": SCHEMA_VERSION,
        "contradictions": [],
        "agreements": [],
        "contradiction_resolved_to_truth": False,
        "model_consensus_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": False,
        "created_at": _utc_now_iso(),
    }


def add_contradiction(
    ledger: dict,
    *,
    seed_id: str,
    task_id: str,
    model_a: str,
    model_b: str,
    claim_a: str,
    claim_b: str,
    source: str = "adjudicator_v2",
) -> dict:
    """Add a contradiction entry. Returns updated ledger.

    Contradictions are NEVER resolved to truth by the system.
    Operator review is ALWAYS required.
    """
    entry = {
        "seed_id": seed_id,
        "task_id": task_id,
        "model_a": model_a,
        "model_b": model_b,
        "claim_a": claim_a,
        "claim_b": claim_b,
        "source": source,
        "resolved_to_truth": False,
        "timestamp": _utc_now_iso(),
    }
    entry["entry_id"] = _entry_id(entry)

    ledger = dict(ledger)
    ledger["contradictions"] = list(ledger.get("contradictions", [])) + [entry]

    # Invariants — always enforced
    ledger["contradiction_resolved_to_truth"] = False
    ledger["model_consensus_is_not_proof"] = True
    ledger["promotion_allowed"] = False
    ledger["operator_review_required"] = True

    return ledger


def add_agreement(
    ledger: dict,
    *,
    seed_id: str,
    task_id: str,
    model_a: str,
    model_b: str,
    shared_claim: str,
    source: str = "adjudicator_v2",
) -> dict:
    """Add an agreement entry. Returns updated ledger.

    Agreement is NOT proof. Model consensus does NOT become truth.
    """
    entry = {
        "seed_id": seed_id,
        "task_id": task_id,
        "model_a": model_a,
        "model_b": model_b,
        "shared_claim": shared_claim,
        "source": source,
        "is_proof": False,
        "timestamp": _utc_now_iso(),
    }
    entry["entry_id"] = _entry_id(entry)

    ledger = dict(ledger)
    ledger["agreements"] = list(ledger.get("agreements", [])) + [entry]

    # Invariants — always enforced
    ledger["contradiction_resolved_to_truth"] = False
    ledger["model_consensus_is_not_proof"] = True
    ledger["promotion_allowed"] = False

    return ledger


def get_contradictions(ledger: dict, seed_id: str | None = None) -> list:
    """Get contradictions, optionally filtered by seed_id."""
    contradictions = ledger.get("contradictions", [])
    if seed_id is not None:
        return [c for c in contradictions if c.get("seed_id") == seed_id]
    return list(contradictions)


def get_agreements(ledger: dict, seed_id: str | None = None) -> list:
    """Get agreements, optionally filtered by seed_id."""
    agreements = ledger.get("agreements", [])
    if seed_id is not None:
        return [a for a in agreements if a.get("seed_id") == seed_id]
    return list(agreements)


def ledger_summary(ledger: dict) -> dict:
    """Summary statistics for the ledger."""
    contradictions = ledger.get("contradictions", [])
    agreements = ledger.get("agreements", [])

    unresolved = sum(
        1 for c in contradictions if not c.get("resolved_to_truth", False)
    )

    unique_seeds = set()
    for c in contradictions:
        unique_seeds.add(c.get("seed_id", ""))
    for a in agreements:
        unique_seeds.add(a.get("seed_id", ""))

    return {
        "total_contradictions": len(contradictions),
        "total_agreements": len(agreements),
        "unresolved_contradictions": unresolved,
        "unique_seeds": len(unique_seeds),
        "contradiction_resolved_to_truth": False,
        "model_consensus_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": len(contradictions) > 0,
    }


def validate_ledger(ledger: dict) -> list[str]:
    """Validate ledger invariants. Returns list of errors (empty = valid)."""
    errors = []

    if ledger.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: expected {SCHEMA_VERSION}, got {ledger.get('schema')}")

    # Core invariants — must ALWAYS hold
    if ledger.get("contradiction_resolved_to_truth") is not False:
        errors.append("contradiction_resolved_to_truth must be False")
    if ledger.get("model_consensus_is_not_proof") is not True:
        errors.append("model_consensus_is_not_proof must be True")
    if ledger.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    # Check individual contradiction entries
    for i, c in enumerate(ledger.get("contradictions", [])):
        if c.get("resolved_to_truth") is not False:
            errors.append(
                f"contradiction[{i}].resolved_to_truth must be False"
            )
        if not c.get("seed_id"):
            errors.append(f"contradiction[{i}] missing seed_id")
        if not c.get("model_a") or not c.get("model_b"):
            errors.append(f"contradiction[{i}] missing model_a or model_b")

    # Check individual agreement entries
    for i, a in enumerate(ledger.get("agreements", [])):
        if a.get("is_proof") is not False:
            errors.append(
                f"agreement[{i}].is_proof must be False"
            )

    # If contradictions exist, operator review must be required
    if len(ledger.get("contradictions", [])) > 0:
        if not ledger.get("operator_review_required"):
            errors.append("operator_review_required must be True when contradictions exist")

    return errors
