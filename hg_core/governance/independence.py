"""
Governance independence (Pack 3): closed-loop detection, reviewer rotation, spot checks.
No closed-loop approvals; reviewer assignment with availability/fatigue; spot checks for batches.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _approval_graph(workspace_root: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return (action_id -> proposer, action_id -> approver) from ledger."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    proposer: Dict[str, str] = {}
    approver: Dict[str, str] = {}
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        payload = ev.get("payload") or {}
        actor = ev.get("actor") or {}
        aid = payload.get("action_id")
        agent = actor.get("agent_id") or ""
        if ev.get("action") == "ACTION_PROPOSED" and aid:
            proposer[aid] = agent
        elif ev.get("action") == "ACTION_APPROVAL_GRANTED" and aid and agent:
            approver[aid] = agent
    return proposer, approver


def check_closed_loop(
    workspace_root: Path,
    requester_id: str,
    approver_id: str,
    *,
    cooldown_lookback_actions: int = 50,
) -> bool:
    """
    Return True if requester_id and approver_id form a closed loop (A approved B, B approved A recently).
    Used to reject high-impact approvals when requester and approver are in same loop.
    """
    if not requester_id or not approver_id or requester_id == approver_id:
        return True  # same identity => treat as closed
    proposer, approver = _approval_graph(Path(workspace_root))
    # Build edges: approver -> proposer (who did they approve for)
    approved_for: Dict[str, Set[str]] = {}
    for aid, app in approver.items():
        prop = proposer.get(aid)
        if prop:
            approved_for.setdefault(app, set()).add(prop)
    # Check: did approver_id ever approve for requester_id? and did requester_id approve for approver_id?
    if approver_id in approved_for and requester_id in approved_for.get(approver_id, set()):
        if requester_id in approved_for and approver_id in approved_for.get(requester_id, set()):
            return True  # closed loop
    return False


def require_independent_review(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    reason: str = "",
) -> str:
    """Emit INDEPENDENT_REVIEW_REQUIRED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "INDEPENDENT_REVIEW_REQUIRED",
        "governance",
        action_id,
        {"action_id": action_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def assign_reviewer(
    *,
    action_id: str,
    reviewer_id: str,
    rationale: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit REVIEWER_ASSIGNED with rationale. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "REVIEWER_ASSIGNED",
        "governance",
        action_id,
        {
            "action_id": action_id,
            "reviewer_id": reviewer_id,
            "rationale": rationale,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def reject_approval_independence(
    *,
    action_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit APPROVAL_REJECTED_BY_INDEPENDENCE_RULE. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "APPROVAL_REJECTED_BY_INDEPENDENCE_RULE",
        "governance",
        action_id,
        {"action_id": action_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def assign_spotcheck(
    *,
    batch_id: str,
    target_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    reason: str = "batch_approval_random_sample",
) -> Tuple[str, str]:
    """
    Emit SPOTCHECK_ASSIGNED and request audit spotcheck. Returns (event_id, spotcheck_id).
    For batch approvals: randomized spot check assignment.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    spot_id = "spa_" + hashlib.sha256(f"{batch_id}:{target_id}:{ts}".encode()).hexdigest()[:16]
    ev_id = emit(
        "SPOTCHECK_ASSIGNED",
        "governance",
        spot_id,
        {
            "spotcheck_assignment_id": spot_id,
            "batch_id": batch_id,
            "target_id": target_id,
            "reason": reason,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    from hg_core.governance.ux.batching import request_audit_spotcheck
    _, req_spot_id = request_audit_spotcheck(
        target_id=target_id,
        reason=reason,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return ev_id, req_spot_id


def build_voice_belief_separation_summary(
    *,
    mimicry_policy_summary: dict[str, Any] | None = None,
    self_model_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mimicry_policy_summary = mimicry_policy_summary if isinstance(mimicry_policy_summary, dict) else {}
    self_model_summary = self_model_summary if isinstance(self_model_summary, dict) else {}
    policy_status = str(mimicry_policy_summary.get("status") or "").strip().lower()
    self_model_status = str(self_model_summary.get("status") or "").strip().lower()
    voice_belief_separated = bool(mimicry_policy_summary.get("voice_belief_separated"))
    grounding_required = bool(mimicry_policy_summary.get("grounding_required"))
    grounded = bool(mimicry_policy_summary.get("safeguard_summary", {}).get("grounded"))
    max_depth = mimicry_policy_summary.get("limits", {}).get("max_mimicry_depth")
    max_emotional_intensity = mimicry_policy_summary.get("limits", {}).get("max_emotional_intensity")

    status = "missing"
    blockers: list[str] = []
    cautions: list[str] = []
    drivers: list[str] = []
    if policy_status == "blocked":
        status = "blocked"
        blockers.append("mimicry_policy_blocked")
    elif policy_status in {"ready", "caution"}:
        status = "healthy" if voice_belief_separated and (not grounding_required or grounded) else "caution"
        if voice_belief_separated:
            drivers.append("voice_belief_separated")
        else:
            blockers.append("voice_and_belief_coupled")
        if grounding_required and grounded:
            drivers.append("grounding_required")
        elif grounding_required and not grounded:
            cautions.append("grounding_missing")
            if status == "healthy":
                status = "caution"
    if self_model_status == "healthy":
        drivers.append("self_model_grounded")
    elif self_model_status in {"partial", "missing"}:
        cautions.append(f"self_model_{self_model_status}")
        if self_model_status == "missing" and status == "healthy":
            status = "caution"
    summary_bits = []
    if voice_belief_separated:
        summary_bits.append("voice separated from durable belief")
    else:
        summary_bits.append("voice and belief still coupled")
    if grounding_required:
        summary_bits.append("grounding required")
    if grounded:
        summary_bits.append("grounded")
    if max_depth is not None:
        summary_bits.append(f"max depth {float(max_depth):.2f}")
    if max_emotional_intensity is not None:
        summary_bits.append(f"max emotion {float(max_emotional_intensity):.2f}")
    return {
        "status": status if status != "missing" else ("healthy" if voice_belief_separated else "missing"),
        "voice_belief_separated": voice_belief_separated,
        "grounding_required": grounding_required,
        "grounded": grounded,
        "policy_status": policy_status or None,
        "self_model_status": self_model_status or None,
        "max_mimicry_depth": max_depth,
        "max_emotional_intensity": max_emotional_intensity,
        "drivers": drivers,
        "cautions": cautions,
        "blockers": blockers,
        "summary": "; ".join(summary_bits) if summary_bits else "voice and belief separation unavailable",
    }
