"""
Metacognition materializer: from SELF_ASSESSMENT_RECORDED, TOOL_OUTCOME_RECORDED, PREDICTION_MADE, EVALUATION_RECORDED
build calibration metrics (brier, bucketed curve) and tool reliability stats. Deterministic and rebuildable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, save_checkpoint


def _outcome_from_evaluation(eval_row: Dict[str, Any]) -> float:
    """Map evaluation to binary outcome for calibration: 1 = success, 0 = fail."""
    score = eval_row.get("score") or {}
    if isinstance(score, dict):
        if score.get("success") is True:
            return 1.0
        if "value" in score:
            try:
                v = float(score["value"])
                return 1.0 if v > 0.5 else 0.0
            except (TypeError, ValueError):
                pass
    if isinstance(score, (int, float)):
        return 1.0 if float(score) > 0.5 else 0.0
    return 0.0


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    self_assessments: List[Dict[str, Any]] = []
    tool_outcomes: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []
    evaluations: List[Dict[str, Any]] = []
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        base = {"event_id": ev.get("event_id"), "ts": ts, "scope_type": scope_type, "scope_id": scope_id, "agent_id": actor.get("agent_id", "")}
        if action == "SELF_ASSESSMENT_RECORDED":
            self_assessments.append({
                **base,
                "assessment_id": payload.get("assessment_id", ""),
                "decision_id": payload.get("decision_id", ""),
                "confidence": payload.get("confidence"),
                "uncertainty_factors": payload.get("uncertainty_factors", []),
                "risk_flags": payload.get("risk_flags", []),
                "recommended_controls": payload.get("recommended_controls", {}),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
            })
        elif action == "TOOL_OUTCOME_RECORDED":
            tool_outcomes.append({
                **base,
                "tool_call_id": payload.get("tool_call_id", ""),
                "tool_name": payload.get("tool_name", ""),
                "inputs_hash": payload.get("inputs_hash", ""),
                "outcome": payload.get("outcome", ""),
                "error_class": payload.get("error_class", ""),
                "latency_ms": payload.get("latency_ms", 0),
                "cost_units": payload.get("cost_units", 0.0),
                "artifact_links": payload.get("artifact_links", []),
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
                "score": payload.get("score", {}),
            })

    eval_by_pred: Dict[str, Dict[str, Any]] = {e.get("prediction_id"): e for e in evaluations if e.get("prediction_id")}
    calibration_timeseries: List[Dict[str, Any]] = []
    for p in predictions:
        pred_id = p.get("prediction_id", "")
        conf = p.get("confidence")
        if conf is None or pred_id not in eval_by_pred:
            continue
        e = eval_by_pred[pred_id]
        outcome = _outcome_from_evaluation(e)
        try:
            c = float(conf)
        except (TypeError, ValueError):
            continue
        brier = (c - outcome) ** 2
        calibration_timeseries.append({
            "prediction_id": pred_id,
            "evaluation_id": e.get("evaluation_id", ""),
            "ts": p.get("ts", ""),
            "confidence": c,
            "outcome": outcome,
            "brier_score": brier,
        })

    bucket_size = 0.1
    calibration_curve: List[Dict[str, Any]] = []
    for i in range(10):
        lo, hi = i * bucket_size, (i + 1) * bucket_size
        points = [x for x in calibration_timeseries if lo <= x["confidence"] < hi]
        avg_outcome = sum(p["outcome"] for p in points) / len(points) if points else 0.0
        calibration_curve.append({"bucket_lo": lo, "bucket_hi": hi, "count": len(points), "avg_outcome": avg_outcome})

    tool_stats: Dict[str, Dict[str, Any]] = {}
    for t in tool_outcomes:
        name = t.get("tool_name", "")
        if name not in tool_stats:
            tool_stats[name] = {"tool_name": name, "total": 0, "success": 0, "fail": 0, "timeout": 0, "partial": 0, "latency_ms_sum": 0}
        tool_stats[name]["total"] += 1
        tool_stats[name]["latency_ms_sum"] += t.get("latency_ms", 0)
        o = t.get("outcome", "fail")
        if o in tool_stats[name]:
            tool_stats[name][o] += 1
    tool_reliability = []
    for name, s in tool_stats.items():
        total = s["total"]
        tool_reliability.append({
            "tool_name": name,
            "total_calls": total,
            "success_count": s.get("success", 0),
            "fail_count": s.get("fail", 0),
            "timeout_count": s.get("timeout", 0),
            "partial_count": s.get("partial", 0),
            "success_rate": s.get("success", 0) / total if total else 0.0,
            "avg_latency_ms": s["latency_ms_sum"] / total if total else 0,
        })

    (root / "self_assessments.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in self_assessments),
        encoding="utf-8",
    )
    (root / "tool_outcomes.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in tool_outcomes),
        encoding="utf-8",
    )
    (root / "calibration_timeseries.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in calibration_timeseries),
        encoding="utf-8",
    )
    (root / "calibration_curve.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in calibration_curve),
        encoding="utf-8",
    )
    (root / "tool_reliability.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in tool_reliability),
        encoding="utf-8",
    )
    save_checkpoint(workspace_root, "metacognition", checkpoint)
