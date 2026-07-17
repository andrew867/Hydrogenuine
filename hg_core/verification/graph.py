"""
VerificationGraph: structured view of sources, checks, robustness for an action.
Gate: critical actions require 2+ independent source groups and robustness threshold.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hg_core.verification.robustness import get_robustness_score


def _iter_verification_events(workspace_root: Path):
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        action = ev.get("action")
        if action in (
            "VERIFICATION_SOURCE_REGISTERED",
            "VERIFICATION_CHECK_PERFORMED",
            "VERIFICATION_ROBUSTNESS_COMPUTED",
        ):
            yield ev


def get_verification_graph(
    workspace_root: Path,
    action_id: Optional[str] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[str, str, str]]]:
    """
    Build VerificationGraph: nodes (sources, checks, robustness), edges (source->check, check->robustness).
    If action_id is given, only include checks and robustness for that action; sources are global.
    Returns (nodes_by_id, edges) where edges are (from_id, to_id, edge_type).
    """
    workspace_root = Path(workspace_root)
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Tuple[str, str, str]] = []

    for ev in _iter_verification_events(workspace_root):
        action = ev.get("action")
        payload = ev.get("payload") or {}
        eid = ev.get("event_id", "")

        if action == "VERIFICATION_SOURCE_REGISTERED":
            sid = payload.get("source_id") or ""
            if not sid:
                continue
            nid = f"source:{sid}"
            nodes[nid] = {
                "type": "source",
                "id": sid,
                "name": payload.get("name", ""),
                "event_id": eid,
            }
            continue

        if action == "VERIFICATION_CHECK_PERFORMED":
            aid = payload.get("action_id")
            if action_id is not None and aid != action_id:
                continue
            check_id = payload.get("check_id") or ""
            sid = payload.get("source_id") or ""
            if not check_id:
                continue
            nid = f"check:{check_id}"
            nodes[nid] = {
                "type": "check",
                "id": check_id,
                "action_id": aid,
                "source_id": sid,
                "result": payload.get("result", ""),
                "event_id": eid,
            }
            if sid:
                edges.append((f"source:{sid}", nid, "PERFORMED"))
            if aid:
                action_nid = f"action:{aid}"
                if action_nid not in nodes:
                    nodes[action_nid] = {"type": "action", "id": aid, "action_id": aid}
                edges.append((nid, action_nid, "FOR_ACTION"))
            continue

        if action == "VERIFICATION_ROBUSTNESS_COMPUTED":
            aid = payload.get("action_id")
            if action_id is not None and aid != action_id:
                continue
            rob_id = payload.get("robustness_id") or ""
            if not rob_id:
                continue
            nid = f"robustness:{rob_id}"
            nodes[nid] = {
                "type": "robustness",
                "id": rob_id,
                "action_id": aid,
                "score": payload.get("score"),
                "event_id": eid,
            }
            action_nid = f"action:{aid}"
            if action_nid not in nodes:
                nodes[action_nid] = {"type": "action", "id": aid, "action_id": aid}
            edges.append((nid, action_nid, "FOR_ACTION"))
            continue

    return nodes, edges


def _get_checks_for_action(workspace_root: Path, action_id: str) -> List[Dict[str, Any]]:
    checks = []
    for ev in _iter_verification_events(workspace_root):
        if ev.get("action") != "VERIFICATION_CHECK_PERFORMED":
            continue
        p = ev.get("payload") or {}
        if p.get("action_id") == action_id:
            checks.append(p)
    return checks


def check_verification_gate(
    workspace_root: Path,
    action_id: str,
    *,
    critical: bool = False,
    min_independent_groups: int = 2,
    min_robustness: float = 0.0,
) -> Tuple[bool, str]:
    """
    Check if action passes verification gate. For critical actions, require at least
    min_independent_groups distinct source_ids with at least one pass each, and
    robustness >= min_robustness. Correlated checks (same source) count as one group.
    Returns (passed, reason).
    """
    workspace_root = Path(workspace_root)
    checks = _get_checks_for_action(workspace_root, action_id)

    if not checks:
        return False, "no_checks"

    # Independent groups = unique source_ids that have at least one pass
    pass_by_source: Set[str] = set()
    for c in checks:
        if c.get("result") == "pass":
            sid = c.get("source_id") or ""
            if sid:
                pass_by_source.add(sid)

    if critical:
        if len(pass_by_source) < min_independent_groups:
            return False, f"insufficient_independent_groups (have {len(pass_by_source)}, need {min_independent_groups})"
        score = get_robustness_score(workspace_root, action_id)
        if score is not None and score < min_robustness:
            return False, f"robustness_below_threshold ({score} < {min_robustness})"

    return True, "ok"
