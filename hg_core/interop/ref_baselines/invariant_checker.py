"""
Interop Pack 6: Invariant checker — machine-checkable invariants over event logs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


INVARIANT_DEFS = [
    {"id": "INV-001", "desc": "No commit without verify+approval", "rule": "commit_requires_approval"},
    {"id": "INV-002", "desc": "No grant without quorum (sensitive scope)", "rule": "grant_requires_quorum"},
    {"id": "INV-003", "desc": "No reuse of expired approvals", "rule": "no_expired_approval_reuse"},
    {"id": "INV-004", "desc": "No trust tier downgrade without exception", "rule": "downgrade_requires_exception"},
    {"id": "INV-005", "desc": "No settlement without quorum proof", "rule": "settlement_requires_quorum_proof"},
]


def _load_events(events_path: Path) -> List[Dict[str, Any]]:
    events = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _check_commit_requires_approval(events: List[Dict[str, Any]]) -> tuple:
    """INV-001: Commit-like actions should have prior approval/verification."""
    commit_actions = {"ACTION_COMMITTED", "CONNECTOR_CALL_EXECUTED"}
    ok = True
    notes = []
    for i, ev in enumerate(events):
        action = ev.get("action") or ""
        if action not in commit_actions:
            continue
        prior = events[:i]
        has_approval = any((p.get("action") or "").startswith("APPROVAL") or "VERIF" in (p.get("action") or "") for p in prior)
        if not has_approval and prior:
            notes.append("event %s has %s without prior approval/verify" % (ev.get("event_id"), action))
            ok = False
    return ok, notes


def _check_grant_requires_quorum(events: List[Dict[str, Any]]) -> tuple:
    """INV-002: CAPABILITY_GRANT_ISSUED for sensitive scope should have prior THRESHOLD_ACTION_FINALIZED."""
    ok = True
    notes = []
    for i, ev in enumerate(events):
        if (ev.get("action") or "") != "CAPABILITY_GRANT_ISSUED":
            continue
        payload = ev.get("payload") or {}
        scope = payload.get("scope") or {}
        scope_id = scope.get("id") or ""
        if "prod" in scope_id.lower() or "sensitive" in str(scope).lower():
            prior = events[:i]
            has_quorum = any((p.get("action") or "") == "THRESHOLD_ACTION_FINALIZED" for p in prior)
            if not has_quorum:
                notes.append("CAPABILITY_GRANT_ISSUED for sensitive-looking scope without prior THRESHOLD_ACTION_FINALIZED")
                ok = False
    return ok, notes


def _check_no_expired_approval_reuse(events: List[Dict[str, Any]]) -> tuple:
    """INV-003: No duplicate receipt_id in APPROVAL_GRANTED (reuse)."""
    seen_receipts = set()
    ok = True
    notes = []
    for ev in events:
        if (ev.get("action") or "") != "APPROVAL_GRANTED":
            continue
        rid = (ev.get("payload") or {}).get("receipt_id")
        if rid:
            if rid in seen_receipts:
                notes.append("duplicate receipt_id in APPROVAL_GRANTED: %s" % rid)
                ok = False
            seen_receipts.add(rid)
    return ok, notes


def _check_downgrade_requires_exception(events: List[Dict[str, Any]]) -> tuple:
    """INV-004: Trust tier downgrade must have TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED."""
    tier_order = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
    last_tier: Optional[int] = None
    ok = True
    notes = []
    exception_grants = set()
    for ev in events:
        action = ev.get("action") or ""
        if action == "TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED":
            payload = ev.get("payload") or {}
            exception_grants.add(payload.get("link_id") or payload.get("ref_id") or "global")
        if action not in ("TRUST_TIER_ACCEPTED", "TRUST_TIER_PROPOSED"):
            continue
        payload = ev.get("payload") or {}
        tier_s = payload.get("tier") or payload.get("trust_tier") or ""
        current = tier_order.get(tier_s)
        if current is None:
            continue
        if last_tier is not None and current < last_tier:
            if not exception_grants:
                notes.append("downgrade from tier %s to %s without TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED" % (last_tier, current))
                ok = False
        last_tier = current
    return ok, notes


def _check_settlement_requires_quorum_proof(events: List[Dict[str, Any]]) -> tuple:
    """INV-005: SETTLEMENT_PUBLISHED must have quorum_proof_artifact_id."""
    ok = True
    notes = []
    for ev in events:
        if (ev.get("action") or "") != "SETTLEMENT_PUBLISHED":
            continue
        q = (ev.get("payload") or {}).get("quorum_proof_artifact_id")
        if not q:
            notes.append("SETTLEMENT_PUBLISHED without quorum_proof_artifact_id")
            ok = False
    return ok, notes


def run_invariant_checker(events_path: Path) -> Dict[str, Any]:
    """
    Run invariant checks over events.jsonl. Returns report with invariants[].id, .ok, .notes.
    """
    events_path = Path(events_path)
    if not events_path.is_file():
        return {"ok": False, "invariants": [], "error": "events file not found"}
    events = _load_events(events_path)
    rule_handlers = {
        "commit_requires_approval": _check_commit_requires_approval,
        "grant_requires_quorum": _check_grant_requires_quorum,
        "no_expired_approval_reuse": _check_no_expired_approval_reuse,
        "downgrade_requires_exception": _check_downgrade_requires_exception,
        "settlement_requires_quorum_proof": _check_settlement_requires_quorum_proof,
    }
    results = []
    overall = True
    for inv in INVARIANT_DEFS:
        rule = inv.get("rule") or ""
        handler = rule_handlers.get(rule)
        if not handler:
            results.append({"id": inv["id"], "desc": inv.get("desc"), "ok": True, "notes": ["stub"]})
            continue
        ok, notes = handler(events)
        if not ok:
            overall = False
        results.append({"id": inv["id"], "desc": inv.get("desc"), "ok": ok, "notes": notes})
    return {"ok": overall, "invariants": results}
