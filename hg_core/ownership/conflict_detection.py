"""Chapter2 conflict detection and R1 arbitration. Ref: .cursor/plans/autonomy/chapter2 SPEC_CONFLICT_RESOLUTION."""
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

from .ownership_ledger import OwnershipLedger
from .ownership_store import OwnershipStore


def detect_scope_overlap(scopes_a: List[Dict[str, Any]], scopes_b: List[Dict[str, Any]]) -> bool:
    """Detect if contributor scopes overlap for the same artifact (or same artifact+component)."""
    for a in scopes_a:
        art_a = a.get("artifact") or ""
        comp_a = a.get("component", "")
        for b in scopes_b:
            art_b = b.get("artifact") or ""
            comp_b = b.get("component", "")
            if art_a and art_a == art_b:
                return True
            if not art_a and not art_b and comp_a and comp_a == comp_b:
                return True
    return False


def can_finalize(store: OwnershipStore, task_id: str, actor: str) -> bool:
    """True iff actor is the current lead (executor) for task_id."""
    rec = store.get_task(task_id)
    if rec.state not in ("acknowledged", "in_progress"):
        return False
    return rec.executor_id == actor


def detect_lead_conflict(claims: List[Dict[str, Any]]) -> bool:
    """True if more than one active lead claim with valid lease."""
    active = [c for c in claims if c.get("lease_valid") is True]
    return len(active) > 1


def run_arbitration_r1(claims: List[Dict[str, Any]], role_priority: Optional[Dict[str, int]] = None) -> str:
    """Deterministic arbitration R1: earliest start_time, then role priority, then lexicographic agent_id."""
    valid = [c for c in claims if c.get("lease_valid") is True]
    if not valid:
        return ""
    if len(valid) == 1:
        return valid[0].get("agent_id", "")
    role_priority = role_priority or {}
    def key(c: Dict[str, Any]) -> tuple:
        start = c.get("start_time") or 0.0
        prio = -(role_priority.get(c.get("agent_id", ""), 0))
        agent = c.get("agent_id", "")
        return (start, prio, agent)
    sorted_claims = sorted(valid, key=key)
    return sorted_claims[0].get("agent_id", "")


def record_arbitration_decision(
    ledger: OwnershipLedger,
    task_id: str,
    winner_agent_id: str,
    claims: List[Dict[str, Any]],
    actor: str = "system",
) -> Dict[str, Any]:
    """Emit arbitration_decision record to ledger (audit trail)."""
    return ledger.append(
        task_id,
        "arbitration_decision",
        actor,
        {"winner_agent_id": winner_agent_id, "claims_count": len(claims), "ts": time.time()},
    )


def attempt_finalize(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    expected_version: int,
) -> Dict[str, Any]:
    """Attempt finalize; if actor is not lead, block and log finalize_unauthorized."""
    if not can_finalize(store, task_id, actor):
        ledger.append(
            task_id,
            "finalize_unauthorized",
            actor,
            {"reason": "not_lead", "task_id": task_id, "ts": time.time()},
            expected_version=expected_version,
        )
        return {"ok": False, "error": "not_lead"}
    return {"ok": True}


def detect_missing_receipt_at_checkpoint(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    checkpoint_id: str,
) -> bool:
    """True if policy requires a receipt at this checkpoint but none exists."""
    from .handoff import can_proceed_from_checkpoint
    return not can_proceed_from_checkpoint(store, ledger, task_id, checkpoint_id)


def has_ownership_conflict(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    checkpoint_id: Optional[str] = None,
) -> bool:
    """True if any conflict: lead conflict, scope overlap, finalize unauthorized, or missing receipt."""
    rec = store.get_task(task_id)
    if rec.state == "contested" and rec.contested_claims and len(rec.contested_claims) > 1:
        return True
    if checkpoint_id and detect_missing_receipt_at_checkpoint(store, ledger, task_id, checkpoint_id):
        return True
    return False


# --- Chapter2 Phase 4: partial ownership, explicit merge step ---


def requires_merge_step_for_critical(
    contributor_scopes: List[Dict[str, Any]],
    artifact_or_component: str,
    critical_artifacts: Optional[List[str]] = None,
) -> bool:
    """
    R3: For critical artifacts, overlapping contributor scopes require an explicit merge step
    (no last-writer-wins). Returns True if a merge step is required before writing to artifact_or_component.
    """
    critical_artifacts = critical_artifacts or []
    if artifact_or_component not in critical_artifacts:
        return False
    for s in contributor_scopes:
        art = s.get("artifact") or s.get("component") or ""
        if art == artifact_or_component:
            return True
    return False
