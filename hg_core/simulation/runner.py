"""
Control Surface Pack 9: Simulation mode — scenario runner, deterministic report, bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _simulations_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "simulations"


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def run_simulation(
    *,
    swarm_id: str,
    scenario_pack: str = "default",
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run simulation scenario pack. Emit SIMULATION_RUN_STARTED, run synthetic scenario,
    emit SIMULATION_RUN_COMPLETED, write SIMULATION_SCORE_REPORT artifact.
    Returns { run_id, report_path, passed }.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    run_id = "sim_" + hashlib.sha256(f"{swarm_id}:{scenario_pack}:{ts}".encode()).hexdigest()[:16]

    emit(
        "SIMULATION_RUN_STARTED",
        "simulation",
        run_id,
        {"run_id": run_id, "swarm_id": swarm_id, "scenario_pack": scenario_pack, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )

    # Deterministic synthetic run: apply same gating as live (e.g. drift preflight)
    from hg_core.drift.api import preflight_drift
    preflight = preflight_drift(workspace_root, score_threshold=0.7)
    blocked = preflight.get("blocked", False)
    score = 0.0 if blocked else 1.0

    root = _simulations_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id,
        "swarm_id": swarm_id,
        "scenario_pack": scenario_pack,
        "ts": ts,
        "score": score,
        "passed": not blocked,
        "gates_blocked": blocked,
        "drift_preflight": preflight,
    }
    report_path = root / f"{run_id}_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    emit(
        "SIMULATION_RUN_COMPLETED",
        "simulation",
        run_id,
        {"run_id": run_id, "ts": _iso_ts(), "passed": report["passed"], "report_path": str(report_path)},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )

    # Append to materialized list for list_simulation_results
    mat = _materialized_root(workspace_root)
    mat.mkdir(parents=True, exist_ok=True)
    sim_list_path = mat / "simulation_runs.jsonl"
    with open(sim_list_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "run_id": run_id,
            "swarm_id": swarm_id,
            "scenario_pack": scenario_pack,
            "ts": ts,
            "passed": report["passed"],
            "report_path": str(report_path),
        }, ensure_ascii=False) + "\n")

    return {"run_id": run_id, "report_path": str(report_path), "passed": report["passed"]}


def list_simulation_results(
    workspace_root: Path,
    swarm_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List simulation runs and reports from materialized simulation_runs.jsonl."""
    mat = _materialized_root(Path(workspace_root))
    rows = _load_jsonl(mat / "simulation_runs.jsonl")
    if swarm_id:
        rows = [r for r in rows if r.get("swarm_id") == swarm_id]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]
