"""EXCITON task selection monitor snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.task_selection.objective_universe import list_universes, load_universe
from hg_runtime.task_selection.schema import STORE_ROOT, now_iso
from hg_runtime.task_selection.task_policy import policy_status

DECISION_DIR = STORE_ROOT / "decisions"
RECEIPT_DIR = STORE_ROOT / "receipts"
CANDIDATE_DIR = STORE_ROOT / "candidates"


def _latest_json(dir_path: Path) -> dict[str, Any] | None:
    if not dir_path.is_dir():
        return None
    files = sorted(dir_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    import json

    return json.loads(files[0].read_text(encoding="utf-8"))


def build_task_selection_monitor_snapshot() -> dict[str, Any]:
    universes = list_universes()
    active = universes[0] if universes else None
    latest_decision = _latest_json(DECISION_DIR)
    latest_receipt = _latest_json(RECEIPT_DIR)

    candidate_count = len(list(CANDIDATE_DIR.glob("*.json"))) if CANDIDATE_DIR.is_dir() else 0

    selected_task = None
    refused_tasks: list[str] = []
    deferred_tasks: list[str] = []
    idle_reflection = None
    verdict = "YELLOW_NO_TASK_SELECTION_YET"
    broker_refs: list[str] = []
    receipt_refs: list[str] = []

    if latest_decision:
        verdict = latest_decision.get("verdict", verdict)
        selected_task = latest_decision.get("selected_candidate_ref")
        refused_tasks = list(latest_decision.get("refused_candidate_refs") or [])
        deferred_tasks = list(latest_decision.get("deferred_candidate_refs") or [])
        idle_reflection = latest_decision.get("idle_reflection_ref")
        if latest_decision.get("broker_decision_ref"):
            broker_refs.append(latest_decision["broker_decision_ref"])
        receipt_refs.append(latest_decision["task_selection_decision_id"])

    if latest_receipt:
        receipt_refs.append(latest_receipt.get("task_selection_receipt_id", ""))

    freshness = now_iso()
    if latest_decision and latest_decision.get("created_at"):
        freshness = latest_decision["created_at"]

    policy = policy_status()
    external_action_green = False  # never fake green for external action

    return {
        "panel_id": "agent_zero_task_selection_monitor",
        "title": "Agent Zero Task Selection Monitor",
        "objective_universe_status": active.status if active else "none",
        "universe_id": active.universe_id if active else None,
        "allowed_scopes": list(active.allowed_objective_scopes) if active else [],
        "candidate_count": candidate_count,
        "selected_task": selected_task,
        "refused_tasks": refused_tasks,
        "deferred_tasks": deferred_tasks,
        "idle_reflection": idle_reflection,
        "authority_boundary_ref": "configs/agent_zero/external_write_authority_policy.json",
        "broker_decision_refs": broker_refs,
        "task_receipt_refs": [r for r in receipt_refs if r],
        "freshness": freshness,
        "verdict": verdict,
        "external_action_autonomous_green": external_action_green,
        "policy_phase": policy.get("phase", 21),
        "live_writes_allowed": policy.get("live_writes_allowed", False),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
