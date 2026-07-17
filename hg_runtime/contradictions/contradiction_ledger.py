"""Contradiction Ledger v2 -- full contradiction ledger with resolution
tracking, type/severity filtering, and invariant enforcement.

Contradictions are NOT resolved to truth. Model consensus is NOT proof.
Promotion is NEVER allowed. Operator review is ALWAYS required when
unresolved entries exist.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from hg_runtime.contradictions.contradiction_types import (
    CONTRADICTION_TYPES,
    RESOLUTION_STATES,
    SEVERITY_LEVELS,
)
from hg_runtime.contradictions.contradiction_receipts import (
    validate_contradiction_receipt,
)

SCHEMA_VERSION = "contradiction_ledger_v2"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _enforce_invariants(ledger: dict) -> dict:
    """Enforce all ledger invariants."""
    ledger["contradiction_resolved_to_truth"] = False
    ledger["model_consensus_is_not_proof"] = True
    ledger["promotion_allowed"] = False

    # operator_review_required when any unresolved entries exist
    has_unresolved = any(
        e.get("resolution_state") in ("unresolved", "needs_source", "needs_operator")
        for e in ledger.get("entries", [])
    )
    ledger["operator_review_required"] = has_unresolved

    return ledger


def create_ledger() -> dict:
    """Create an empty contradiction ledger v2."""
    return {
        "schema": SCHEMA_VERSION,
        "entries": [],
        "contradiction_resolved_to_truth": False,
        "model_consensus_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": False,
        "created_at": _utc_now_iso(),
    }


def add_entry(ledger: dict, receipt: dict) -> dict:
    """Add a contradiction receipt to the ledger. Returns new ledger (immutable).

    Contradictions are NEVER resolved to truth by the system.
    Operator review is ALWAYS required when unresolved entries exist.
    """
    new_ledger = copy.deepcopy(ledger)
    new_ledger["entries"] = list(new_ledger.get("entries", [])) + [copy.deepcopy(receipt)]
    new_ledger = _enforce_invariants(new_ledger)
    return new_ledger


def resolve_entry(
    ledger: dict,
    contradiction_id: str,
    *,
    resolution_state: str,
    resolver: str = "operator",
) -> dict:
    """Resolve a contradiction entry in the ledger.

    resolver must be "operator" or "gate" -- NOT "model", NOT "system".
    If resolver is "model" or "system", force resolution_state to "needs_operator".
    """
    new_ledger = copy.deepcopy(ledger)

    # Reject non-authorized resolvers
    actual_resolution = resolution_state
    if resolver not in ("operator", "gate"):
        actual_resolution = "needs_operator"

    for entry in new_ledger.get("entries", []):
        if entry.get("contradiction_id") == contradiction_id:
            entry["resolution_state"] = actual_resolution
            entry["resolved_by"] = resolver if resolver in ("operator", "gate") else "needs_operator"
            entry["resolved_at"] = _utc_now_iso()
            break

    new_ledger = _enforce_invariants(new_ledger)
    return new_ledger


def get_unresolved(ledger: dict) -> list:
    """Get all unresolved entries."""
    return [
        e for e in ledger.get("entries", [])
        if e.get("resolution_state") == "unresolved"
    ]


def get_by_type(ledger: dict, contradiction_type: str) -> list:
    """Get entries filtered by contradiction_type."""
    return [
        e for e in ledger.get("entries", [])
        if e.get("contradiction_type") == contradiction_type
    ]


def get_critical(ledger: dict) -> list:
    """Get entries with severity == 'critical'."""
    return [
        e for e in ledger.get("entries", [])
        if e.get("severity") == "critical"
    ]


def ledger_summary(ledger: dict) -> dict:
    """Summary statistics for the ledger.

    Counts by type, severity, resolution state, and unresolved count.
    """
    entries = ledger.get("entries", [])

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_resolution: dict[str, int] = {}

    for entry in entries:
        ct = entry.get("contradiction_type", "unknown")
        by_type[ct] = by_type.get(ct, 0) + 1

        sev = entry.get("severity", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1

        rs = entry.get("resolution_state", "unknown")
        by_resolution[rs] = by_resolution.get(rs, 0) + 1

    unresolved_count = by_resolution.get("unresolved", 0)

    return {
        "total_entries": len(entries),
        "by_type": by_type,
        "by_severity": by_severity,
        "by_resolution_state": by_resolution,
        "unresolved_count": unresolved_count,
        "contradiction_resolved_to_truth": False,
        "model_consensus_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": unresolved_count > 0,
    }


def validate_ledger(ledger: dict) -> list[str]:
    """Validate ledger invariants. Returns list of errors (empty = valid)."""
    errors = []

    if ledger.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: expected {SCHEMA_VERSION}, got {ledger.get('schema')}")

    if ledger.get("contradiction_resolved_to_truth") is not False:
        errors.append("contradiction_resolved_to_truth must be False")
    if ledger.get("model_consensus_is_not_proof") is not True:
        errors.append("model_consensus_is_not_proof must be True")
    if ledger.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    entries = ledger.get("entries", [])
    unresolved = [e for e in entries if e.get("resolution_state") == "unresolved"]
    if unresolved and not ledger.get("operator_review_required"):
        errors.append("operator_review_required must be True when unresolved entries exist")

    for i, entry in enumerate(entries):
        if entry.get("contradiction_resolved_to_truth") is not False:
            errors.append(f"entries[{i}].contradiction_resolved_to_truth must be False")
        if entry.get("promotion_allowed") is not False:
            errors.append(f"entries[{i}].promotion_allowed must be False")

        ct = entry.get("contradiction_type")
        if ct not in CONTRADICTION_TYPES:
            errors.append(f"entries[{i}] unknown contradiction_type: {ct}")

    return errors
