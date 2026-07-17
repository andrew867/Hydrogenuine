"""Demo-mode seed data generator for workflows, runs, approvals, and metrics."""

import json
import random
import time
from pathlib import Path
from typing import Any


def _workspace_workflows() -> list[str]:
    try:
        from hg_lib.config import get_workspace_root

        reg_path = get_workspace_root() / "memory" / "automation" / "dag_registry.json"
        if reg_path.exists():
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                keys = [str(k) for k in data.keys()]
                if keys:
                    return keys
    except Exception:
        pass
    return ["workflow-a", "workflow-b", "workflow-c", "workflow-d"]


def _profile_workflows(profile_name: str) -> list[str]:
    workflows = _workspace_workflows()
    if profile_name == "small":
        return workflows[:2]
    if profile_name == "large":
        return workflows
    return workflows[: min(4, len(workflows))]


def load_seed_profile(profile_name: str = "medium") -> dict[str, Any]:
    """Load a named seed profile."""
    profiles = {
        "small": {
            "profile_name": "small",
            "workflows": _profile_workflows("small"),
            "run_history": {"days": 7, "avg_runs_per_day_per_workflow": 2, "failure_rate": 0.05, "degraded_rate": 0.1, "include_deadletters": True},
            "metrics_rollups": {"include_cost": True, "include_sla_weekly": True},
        },
        "medium": {
            "profile_name": "medium",
            "workflows": _profile_workflows("medium"),
            "run_history": {"days": 30, "avg_runs_per_day_per_workflow": 4, "failure_rate": 0.05, "degraded_rate": 0.1, "include_deadletters": True},
            "metrics_rollups": {"include_cost": True, "include_sla_weekly": True},
        },
        "large": {
            "profile_name": "large",
            "workflows": _profile_workflows("large"),
            "run_history": {"days": 90, "avg_runs_per_day_per_workflow": 8, "failure_rate": 0.05, "degraded_rate": 0.1, "include_deadletters": True},
            "metrics_rollups": {"include_cost": True, "include_sla_weekly": True},
        },
    }
    return profiles.get(profile_name, profiles["medium"]).copy()


def generate_seed_data(profile: dict[str, Any], output_dir: str | Path | None = None, rng_seed: int = 7) -> dict[str, Any]:
    """Generate synthetic workflow data and optionally write JSON outputs."""
    output_dir = Path(output_dir) if output_dir else None
    rng = random.Random(rng_seed)
    workflows = profile.get("workflows", [])
    run_history = profile.get("run_history", {})
    days = run_history.get("days", 30)
    avg_per_day = run_history.get("avg_runs_per_day_per_workflow", 4)
    failure_rate = run_history.get("failure_rate", 0.05)
    degraded_rate = run_history.get("degraded_rate", 0.1)
    include_dlq = run_history.get("include_deadletters", True)

    out: dict[str, Any] = {"workflows": [], "runs": [], "approvals": [], "deadletters": [], "metrics": {}}

    for wf_id in workflows:
        out["workflows"].append({"id": wf_id, "name": wf_id, "status": "active", "readiness": "supervised"})

    now = time.time()
    run_id = 0
    for _ in range(days):
        for wf_id in workflows:
            n = max(0, int(avg_per_day + rng.gauss(0, 1)))
            for _ in range(n):
                run_id += 1
                r = rng.random()
                if r < failure_rate and include_dlq:
                    status = "failed"
                    out["deadletters"].append({"id": f"dlq-{run_id}", "run_id": f"run-{run_id}", "workflow_id": wf_id})
                elif r < failure_rate + degraded_rate:
                    status = "degraded"
                else:
                    status = "completed"
                out["runs"].append({
                    "run_id": f"run-{run_id}",
                    "graph_id": wf_id,
                    "status": status,
                    "started_at": now - (run_id * 60),
                    "ended_at": now - (run_id * 60) + 30,
                })
                out["approvals"].append({"id": f"app-{run_id}", "timestamp": now - run_id, "decision": "approved"})

    out["metrics"] = {"period": "daily", "cost": {"runs_24h": len(out["runs"])}, "sla": {"success_ratio": 1 - failure_rate}}

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "workflows.json").write_text(json.dumps(out["workflows"], indent=2), encoding="utf-8")
        (output_dir / "runs.json").write_text(json.dumps(out["runs"], indent=2), encoding="utf-8")
        (output_dir / "approvals.json").write_text(json.dumps(out["approvals"], indent=2), encoding="utf-8")
        (output_dir / "deadletters.json").write_text(json.dumps(out["deadletters"], indent=2), encoding="utf-8")
        (output_dir / "metrics.json").write_text(json.dumps(out["metrics"], indent=2), encoding="utf-8")

    return out
