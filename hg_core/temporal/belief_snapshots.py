"""
Belief snapshot: deterministic "what did we believe at time T" from ledger prefix only.
No hindsight; derived from events with ts <= at_ts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_writer import iterate_events


def build_belief_snapshot(
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    at_ts: str,
) -> Dict[str, Any]:
    """
    Build belief state at at_ts from ledger prefix (all events in scope with ts <= at_ts).
    Returns deterministic snapshot: decisions, observations, predictions, evaluations, causal_links, episodes.
    """
    workspace_root = Path(workspace_root)
    decisions: List[Dict[str, Any]] = []
    observations: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []
    evaluations: List[Dict[str, Any]] = []
    causal_links: List[Dict[str, Any]] = []
    episodes: List[Dict[str, Any]] = []
    events_included: List[str] = []

    for ev in iterate_events(workspace_root, scope_type=scope_type, scope_id=scope_id):
        ts = ev.get("ts") or ""
        if ts > at_ts:
            continue
        events_included.append(ev.get("event_id", ""))
        action = ev.get("action")
        payload = ev.get("payload") or {}
        base = {"event_id": ev.get("event_id"), "ts": ts}
        if action in ("DECISION_PROPOSED", "DECISION_COMMITTED"):
            decisions.append({
                **base,
                "decision_id": payload.get("decision_id", ev.get("object", {}).get("id", "")),
                "action": action,
                "based_on_claim_ids": payload.get("based_on_claim_ids", []),
                "value_weights": payload.get("value_weights", []),
            })
        elif action == "OBSERVATION_RECORDED":
            observations.append({
                **base,
                "observation_id": payload.get("observation_id", ""),
                "signal_id": payload.get("signal_id", ""),
            })
        elif action == "PREDICTION_MADE":
            predictions.append({
                **base,
                "prediction_id": payload.get("prediction_id", ""),
                "decision_id": payload.get("decision_id", ""),
                "confidence": payload.get("confidence"),
            })
        elif action == "EVALUATION_RECORDED":
            evaluations.append({
                **base,
                "evaluation_id": payload.get("evaluation_id", ""),
                "prediction_id": payload.get("prediction_id", ""),
            })
        elif action == "CAUSAL_LINK_RECORDED":
            causal_links.append({
                **base,
                "link_id": payload.get("link_id", ""),
                "cause_refs": payload.get("cause_refs", []),
                "effect_refs": payload.get("effect_refs", []),
                "status": payload.get("status", ""),
            })
        elif action == "EPISODE_STARTED":
            episodes.append({
                **base,
                "episode_id": payload.get("episode_id", ""),
                "name": payload.get("name", ""),
                "start_ts": payload.get("start_ts", ""),
            })
        elif action == "EPISODE_ENDED":
            for ep in episodes:
                if ep.get("episode_id") == payload.get("episode_id"):
                    ep["end_ts"] = payload.get("end_ts", "")
                    break

    return {
        "at_ts": at_ts,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "decisions": decisions,
        "observations": observations,
        "predictions": predictions,
        "evaluations": evaluations,
        "causal_links": causal_links,
        "episodes": episodes,
        "event_count": len(events_included),
    }
