"""Pack 14: Cost ceilings and runaway."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from hg_core.ledger import emit

BUDGET_CEILING_REACHED = "BUDGET_CEILING_REACHED"
RUNAWAY_DETECTED = "RUNAWAY_DETECTED"
SAFE_DEGRADE_APPLIED = "SAFE_DEGRADE_APPLIED"


def check_budget_ceiling(current: float, ceiling: float, budget_type: str, workspace_root: Path, scope: Dict, actor: Dict):
    if current >= ceiling:
        eid = emit(BUDGET_CEILING_REACHED, "budget", budget_type, {"current": current, "ceiling": ceiling}, scope=scope, actor=actor, workspace_root=workspace_root)
        return True, eid
    return False, ""


def record_runaway_detected(workspace_root: Path, scope: Dict, actor: Dict, reason: str = "") -> str:
    return emit(RUNAWAY_DETECTED, "safety", "runaway", {"reason": reason or "loop"}, scope=scope, actor=actor, workspace_root=workspace_root)


def apply_safe_degrade(workspace_root: Path, scope: Dict, actor: Dict, mode: str = "plan_only", incident_candidate_id: str = "") -> str:
    return emit(SAFE_DEGRADE_APPLIED, "safety", "degrade", {"mode": mode, "incident_candidate_id": incident_candidate_id}, scope=scope, actor=actor, workspace_root=workspace_root)
