"""
Coalition detection: approval rings, correlated errors, delegation cycles, verifier monoculture.
Emit COALITION_SIGNAL_DETECTED; list_coalition_signals for API.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _iter_scope_events(workspace_root: Path):
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        yield ev


def _detect_approval_ring(workspace_root: Path) -> Optional[Dict[str, Any]]:
    """
    Detect approval ring: A approved action by B, B by C, C by A (cycle of approver -> action proposer).
    Build graph: action_id -> approver_id (from ACTION_APPROVAL_GRANTED), action_id -> proposer (from ACTION_PROPOSED actor).
    A ring is: approver_1 approved action_1 (proposed by X), approver_2 approved action_2 (proposed by approver_1), ...
    until someone approved an action proposed by approver_1. So we need action -> (proposer, approver). Cycle in (proposer, approver) chain.
    Simplified: collect (actor_id who granted, actor_id from proposal if available). We don't have proposal actor in ACTION_APPROVAL_GRANTED.
    So: from ACTION_PROPOSED we have actor.agent_id = proposer, action_id. From ACTION_APPROVAL_GRANTED we have actor.agent_id = approver, action_id.
    So per action: proposer, approver. Graph: proposer -> approver (approver approved proposer's action). Ring: cycle in proposer->approver.
    """
    actions: Dict[str, Dict[str, str]] = {}  # action_id -> {proposer, approver}
    for ev in _iter_scope_events(workspace_root):
        payload = ev.get("payload") or {}
        actor = ev.get("actor") or {}
        aid = payload.get("action_id") or payload.get("work_item_id")
        agent = actor.get("agent_id") or ""
        if ev.get("action") == "ACTION_PROPOSED" and aid:
            actions[aid] = actions.get(aid) or {}
            actions[aid]["proposer"] = agent
        elif ev.get("action") == "ACTION_APPROVAL_GRANTED" and aid and agent:
            actions[aid] = actions.get(aid) or {}
            actions[aid]["approver"] = agent
    # Build directed edge: proposer -> approver (for each action)
    edges: List[Tuple[str, str]] = []
    for aid, v in actions.items():
        p, a = v.get("proposer"), v.get("approver")
        if p and a and p != a:
            edges.append((p, a))
    # Find cycle: DFS
    out_edges: Dict[str, List[str]] = {}
    for u, v in edges:
        out_edges.setdefault(u, []).append(v)
    for start in out_edges:
        stack: List[Tuple[str, List[str]]] = [(start, [start])]
        seen_cycle: Set[str] = set()
        while stack:
            node, path = stack.pop()
            for n in out_edges.get(node, []):
                if n == start and len(path) >= 2:
                    return {
                        "signal_type": "approval_ring",
                        "participants": list(path),
                        "evidence_refs": [],
                    }
                if n in path:
                    continue
                if n in seen_cycle:
                    continue
                stack.append((n, path + [n]))
            seen_cycle.add(node)
    return None


def _detect_verifier_monoculture(workspace_root: Path) -> Optional[Dict[str, Any]]:
    """Verifier monoculture: single source_id accounts for all verification checks for an action (or globally)."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    action_sources: Dict[str, Set[str]] = {}
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if ev.get("action") != "VERIFICATION_CHECK_PERFORMED":
            continue
        p = ev.get("payload") or {}
        aid = p.get("action_id") or "_global"
        sid = p.get("source_id") or ""
        if sid:
            action_sources.setdefault(aid, set()).add(sid)
    for aid, sources in action_sources.items():
        if len(sources) == 1 and len(list(_checks_for_action(workspace_root, aid))) >= 2:
            return {
                "signal_type": "verifier_monoculture",
                "action_id": aid,
                "source_id": list(sources)[0],
                "evidence_refs": [],
            }
    return None


def _checks_for_action(workspace_root: Path, action_id: str) -> List[Dict[str, Any]]:
    checks = []
    for ev in _iter_scope_events(workspace_root):
        if ev.get("action") != "VERIFICATION_CHECK_PERFORMED":
            continue
        p = ev.get("payload") or {}
        if p.get("action_id") == action_id:
            checks.append(p)
    return checks


def detect_coalition_signals(
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    *,
    emit_events: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run coalition detectors (approval ring, verifier monoculture). Optionally emit COALITION_SIGNAL_DETECTED for each.
    Returns list of signal dicts (signal_type, evidence_refs, ...).
    """
    workspace_root = Path(workspace_root)
    signals: List[Dict[str, Any]] = []
    ts = _iso_ts()

    ring = _detect_approval_ring(workspace_root)
    if ring:
        ring["ts"] = ts
        signals.append(ring)
        if emit_events:
            emit(
                "COALITION_SIGNAL_DETECTED",
                "coalition",
                "ring_" + ts.replace(":", "").replace("-", "")[:14],
                ring,
                scope=scope,
                actor=actor,
                workspace_root=workspace_root,
            )

    mono = _detect_verifier_monoculture(workspace_root)
    if mono:
        mono["ts"] = ts
        signals.append(mono)
        if emit_events:
            emit(
                "COALITION_SIGNAL_DETECTED",
                "coalition",
                "mono_" + (mono.get("action_id") or "global")[:20],
                mono,
                scope=scope,
                actor=actor,
                workspace_root=workspace_root,
            )

    return signals


def list_coalition_signals(
    workspace_root: Path,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Return COALITION_SIGNAL_DETECTED events from ledger (most recent first)."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    out: List[Dict[str, Any]] = []
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if ev.get("action") != "COALITION_SIGNAL_DETECTED":
            continue
        payload = (ev.get("payload") or {}).copy()
        payload["event_id"] = ev.get("event_id")
        payload["ts"] = ev.get("ts") or payload.get("ts")
        out.append(payload)
    out.sort(key=lambda x: x.get("ts") or "", reverse=True)
    return out[:limit]
