"""
Control Surface Pack 5: Benchmark scenario runner — load scenario, run/consume event stream, scoring, report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def run_benchmark_scenario(
    scenario_path: Path,
    *,
    bundle_dir: Optional[Path] = None,
    event_stream: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Load scenario definition (JSON with rubric, weights), run simulated or bundle event stream,
    apply scoring rubric, return score report with references.
    """
    scenario_path = Path(scenario_path)
    report: Dict[str, Any] = {
        "scenario_id": None,
        "result": "fail",
        "score": 0.0,
        "max_score": 0.0,
        "breakdown": [],
        "bundle_ref": None,
    }

    if not scenario_path.exists():
        report["error"] = "scenario file not found"
        return report

    try:
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    except Exception as e:
        report["error"] = str(e)
        return report

    scenario_id = scenario.get("scenario_id") or scenario.get("id") or scenario_path.stem
    report["scenario_id"] = scenario_id
    rubric = scenario.get("rubric", [])
    if not rubric:
        rubric = [{"id": "default", "weight": 1.0, "description": "Complete run"}]
    max_score = sum(r.get("weight", 1.0) for r in rubric)
    report["max_score"] = max_score

    events: List[Dict[str, Any]] = []
    if event_stream is not None:
        events = event_stream
    elif bundle_dir:
        bundle_path = Path(bundle_dir) / "events.jsonl"
        if bundle_path.exists():
            for line in bundle_path.read_text(encoding="utf-8").strip().split("\n"):
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            report["bundle_ref"] = str(bundle_dir)

    # Simple scoring: one point per rubric item if we have events
    breakdown: List[Dict[str, Any]] = []
    score = 0.0
    for r in rubric:
        rid = r.get("id", "item")
        weight = r.get("weight", 1.0)
        # Pass if we have at least one event (or scenario says how to score)
        passed = len(events) > 0 or scenario.get("empty_ok")
        if passed:
            score += weight
        breakdown.append({"id": rid, "weight": weight, "passed": passed})
    report["breakdown"] = breakdown
    report["score"] = score
    report["result"] = "pass" if score >= max_score * 0.5 else "fail"
    return report
