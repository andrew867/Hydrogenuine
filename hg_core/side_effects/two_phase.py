"""
Two-phase commit: propose -> approval requested -> grant/deny -> execute (with receipt) -> verify (independent) -> commit.
Receipt artifact mandatory for execute; verification must be independent (verify_action records verifier result).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_proposal, write_receipt


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def propose_action(
    *,
    work_item_id: str,
    tool_name: str,
    idempotency_key: str,
    intended_effects: List[str],
    risk_flags: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ACTION_PROPOSED and ACTION_APPROVAL_REQUESTED. Write proposal artifact. Returns action_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    action_id = "act_" + hashlib.sha256(f"{work_item_id}:{tool_name}:{idempotency_key}".encode()).hexdigest()[:16]
    proposal = {
        "action_id": action_id,
        "work_item_id": work_item_id,
        "tool_name": tool_name,
        "idempotency_key": idempotency_key,
        "intended_effects": intended_effects,
        "risk_flags": risk_flags,
        "ts": ts,
    }
    write_proposal(workspace_root, action_id, proposal)
    payload = {
        "action_id": action_id,
        "work_item_id": work_item_id,
        "tool_name": tool_name,
        "idempotency_key": idempotency_key,
        "intended_effects": intended_effects,
        "risk_flags": risk_flags,
        "ts": ts,
        "receipt_required": True,
        "verification_required": True,
        "proposal_artifact_id": action_id,
    }
    emit("ACTION_PROPOSED", "action", action_id, payload, scope=scope, actor=actor, workspace_root=workspace_root)
    emit(
        "ACTION_APPROVAL_REQUESTED",
        "action",
        action_id,
        {"action_id": action_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return action_id


def grant_approval(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ACTION_APPROVAL_GRANTED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"action_id": action_id, "ts": ts}
    return emit(
        "ACTION_APPROVAL_GRANTED",
        "action",
        action_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def deny_approval(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ACTION_APPROVAL_DENIED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"action_id": action_id, "reason": reason, "ts": ts}
    return emit(
        "ACTION_APPROVAL_DENIED",
        "action",
        action_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def execute_action(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    outcome: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> str:
    """Write receipt artifact (mandatory), emit ACTION_EXECUTED with receipt_artifact_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    receipt = {"action_id": action_id, "ts": ts, "outcome": outcome}
    write_receipt(workspace_root, action_id, receipt)
    payload = {"action_id": action_id, "ts": ts, "receipt_artifact_id": action_id, "outcome_summary": outcome}
    return emit(
        "ACTION_EXECUTED",
        "action",
        action_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def verify_action(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    verified: bool,
    verifier_note: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ACTION_VERIFIED (independent verification; records verifier result)."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"action_id": action_id, "verified": verified, "verifier_note": verifier_note, "ts": ts}
    return emit(
        "ACTION_VERIFIED",
        "action",
        action_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def commit_action(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    require_verification_gate: bool = False,
    critical: bool = False,
) -> str:
    """
    Emit ACTION_COMMITTED.
    If require_verification_gate is True (Differentiators Pack 1), run check_verification_gate
    before commit; on failure raise ValueError so commit is blocked.
    """
    workspace_root = Path(workspace_root or ".")
    if require_verification_gate:
        from hg_core.verification import check_verification_gate
        passed, reason = check_verification_gate(
            workspace_root, action_id, critical=critical, min_independent_groups=2
        )
        if not passed:
            raise ValueError(f"Verification gate failed: {reason}")
    ts = _iso_ts()
    payload = {"action_id": action_id, "ts": ts}
    return emit(
        "ACTION_COMMITTED",
        "action",
        action_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
