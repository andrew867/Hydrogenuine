"""
Temporal indexer: from EPISODE_*, CAUSAL_LINK_RECORDED, BRANCH_* build episodes, timeline, causal_links, branches.
Deterministic and rebuildable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, save_checkpoint


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    episodes: List[Dict[str, Any]] = []
    episode_ends: Dict[str, Dict[str, Any]] = {}
    timeline: List[Dict[str, Any]] = []
    causal_links: List[Dict[str, Any]] = []
    branches: List[Dict[str, Any]] = []
    branch_predictions: List[Dict[str, Any]] = []
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        base = {"event_id": ev.get("event_id"), "ts": ts, "scope_type": scope_type, "scope_id": scope_id, "agent_id": actor.get("agent_id", "")}
        timeline.append({**base, "action": action})
        if action == "EPISODE_STARTED":
            episodes.append({
                **base,
                "episode_id": payload.get("episode_id", ""),
                "name": payload.get("name", ""),
                "start_ts": payload.get("start_ts", ts),
                "end_ts": None,
                "summary_artifact_id": "",
                "participants": payload.get("participants", []),
                "tags": payload.get("tags", []),
            })
        elif action == "EPISODE_ENDED":
            ep_id = payload.get("episode_id", "")
            for ep in episodes:
                if ep.get("episode_id") == ep_id:
                    ep["end_ts"] = payload.get("end_ts", ts)
                    ep["summary_artifact_id"] = payload.get("summary_artifact_id", "")
                    break
        elif action == "EPISODE_SUMMARY_PUBLISHED":
            ep_id = payload.get("episode_id", "")
            for ep in episodes:
                if ep.get("episode_id") == ep_id:
                    ep["summary_artifact_id"] = payload.get("summary_artifact_id", "")
                    break
        elif action == "CAUSAL_LINK_RECORDED":
            causal_links.append({
                **base,
                "link_id": payload.get("link_id", ""),
                "cause_refs": payload.get("cause_refs", []),
                "effect_refs": payload.get("effect_refs", []),
                "strength": payload.get("strength"),
                "type": payload.get("type", "contributing"),
                "status": payload.get("status", "hypothesized"),
                "mechanism_artifact_id": payload.get("mechanism_artifact_id", ""),
            })
        elif action == "BRANCH_PROPOSED":
            branches.append({
                **base,
                "branch_id": payload.get("branch_id", ""),
                "decision_id": payload.get("decision_id", ""),
                "option_id": payload.get("option_id", ""),
                "notes_artifact_id": payload.get("notes_artifact_id", ""),
                "closed": False,
                "close_reason": "",
            })
        elif action == "BRANCH_PREDICTION_MADE":
            branch_predictions.append({
                **base,
                "branch_id": payload.get("branch_id", ""),
                "decision_id": payload.get("decision_id", ""),
                "option_id": payload.get("option_id", ""),
                "prediction_id": payload.get("prediction_id", ""),
                "metric": payload.get("metric", {}),
                "expected": payload.get("expected", {}),
                "deadline": payload.get("deadline", ""),
                "confidence": payload.get("confidence"),
            })
        elif action == "BRANCH_CLOSED":
            for b in branches:
                if b.get("branch_id") == payload.get("branch_id", ""):
                    b["closed"] = True
                    b["close_reason"] = payload.get("reason", "")
                    break

    with open(root / "episodes.jsonl", "w", encoding="utf-8") as f:
        for r in episodes:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "timeline.jsonl", "w", encoding="utf-8") as f:
        for r in timeline:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "causal_links.jsonl", "w", encoding="utf-8") as f:
        for r in causal_links:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "branches.jsonl", "w", encoding="utf-8") as f:
        for r in branches:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "branch_predictions.jsonl", "w", encoding="utf-8") as f:
        for r in branch_predictions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "temporal", checkpoint)
