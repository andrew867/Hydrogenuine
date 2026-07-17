"""
Decision / prediction / evaluation materializer from ledger events.
Output: decisions.jsonl, predictions.jsonl, evaluations.jsonl. Supports incremental (rebuild=False).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, load_checkpoint, save_checkpoint


def _state_path(root: Path) -> Path:
    return root / "decision_state.json"


def _load_state(root: Path) -> Optional[tuple]:
    path = _state_path(root)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    decisions = data.get("decisions")
    predictions = data.get("predictions")
    evaluations = data.get("evaluations")
    checkpoint = data.get("checkpoint")
    if not isinstance(decisions, list) or not isinstance(predictions, list) or not isinstance(evaluations, list):
        return None
    if not isinstance(checkpoint, dict):
        return None
    return (decisions, predictions, evaluations, checkpoint)


def _save_state(
    root: Path,
    decisions: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    evaluations: List[Dict[str, Any]],
    checkpoint: Dict[str, str],
) -> None:
    path = _state_path(root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"decisions": decisions, "predictions": predictions, "evaluations": evaluations, "checkpoint": checkpoint},
            f,
            ensure_ascii=False,
        )


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    decisions_path = root / "decisions.jsonl"
    predictions_path = root / "predictions.jsonl"
    evaluations_path = root / "evaluations.jsonl"
    checkpoint: Dict[str, str] = {}
    decisions: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []
    evaluations: List[Dict[str, Any]] = []
    past_checkpoint: Dict[str, bool] = {}
    loaded = False

    if not rebuild:
        loaded_data = _load_state(root)
        if loaded_data is not None:
            decisions, predictions, evaluations, checkpoint = loaded_data
            decisions = list(decisions)
            predictions = list(predictions)
            evaluations = list(evaluations)
            checkpoint = dict(checkpoint)
            loaded = True

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        eid = ev.get("event_id", "")
        if loaded and scope_key in checkpoint:
            if not past_checkpoint.get(scope_key):
                if eid == checkpoint[scope_key]:
                    past_checkpoint[scope_key] = True
                continue
        checkpoint[scope_key] = eid
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        base = {"event_id": eid, "ts": ts, "scope_type": scope_type, "scope_id": scope_id, "agent_id": actor.get("agent_id", "")}
        if action in ("DECISION_PROPOSED", "DECISION_COMMITTED"):
            decisions.append({
                **base,
                "action": action,
                "decision_id": payload.get("decision_id", ev.get("object", {}).get("id", "")),
                "title": payload.get("title", ""),
                "chosen_option_id": payload.get("chosen_option_id", ""),
                "based_on_claim_ids": payload.get("based_on_claim_ids", []),
                "value_weights": payload.get("value_weights", []),
                "context_ref": payload.get("context_ref", {}),
                "produced_artifact_ids": payload.get("produced_artifact_ids", []),
            })
        elif action == "PREDICTION_MADE":
            predictions.append({
                **base,
                "prediction_id": payload.get("prediction_id", ""),
                "decision_id": payload.get("decision_id", ""),
                "metric": payload.get("metric", {}),
                "expected": payload.get("expected", {}),
                "deadline": payload.get("deadline", ""),
                "confidence": payload.get("confidence"),
            })
        elif action == "EVALUATION_RECORDED":
            evaluations.append({
                **base,
                "evaluation_id": payload.get("evaluation_id", ""),
                "prediction_id": payload.get("prediction_id", ""),
                "observed": payload.get("observed", {}),
                "score": payload.get("score", {}),
                "incident": payload.get("incident", {}),
                "links": payload.get("links", {}),
            })

    with open(decisions_path, "w", encoding="utf-8") as f:
        for r in decisions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(predictions_path, "w", encoding="utf-8") as f:
        for r in predictions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(evaluations_path, "w", encoding="utf-8") as f:
        for r in evaluations:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "decision", checkpoint)
    _save_state(root, decisions, predictions, evaluations, checkpoint)
