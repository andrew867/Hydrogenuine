"""
Cost accounting (K3): run trace budget fields, daily aggregation.

Run trace must include budget_used, budget_remaining (from limit - used).
Daily aggregation: sum budget_used per workflow/destination per day.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DAILY_AGGREGATION_DIR = "memory/automation/daily_budget"
DAILY_AGGREGATION_FILE = "daily_{date}.json"


def trace_budget_fields(
    budget_used: Dict[str, float],
    budget_limits: Dict[str, float],
) -> Dict[str, Any]:
    """
    Build trace fields for K3: budget_used, budget_remaining, cost_estimate (placeholder).
    """
    remaining: Dict[str, float] = {}
    for k, limit in (budget_limits or {}).items():
        used = float((budget_used or {}).get(k, 0.0))
        remaining[k] = max(0.0, float(limit) - used)
    return {
        "budget_used": dict(budget_used or {}),
        "budget_remaining": remaining,
        "budget_limits": dict(budget_limits or {}),
    }


def aggregate_daily(
    workspace_root: Path,
    workflow_id: str,
    run_id: str,
    budget_used: Dict[str, float],
    destination: Optional[str] = None,
) -> None:
    """
    Append run's budget_used to daily aggregation for workflow (and optional destination).
    File: memory/automation/daily_budget/daily_YYYY-MM-DD.json
    """
    root = Path(workspace_root)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = root / DAILY_AGGREGATION_DIR / DAILY_AGGREGATION_FILE.format(date=date)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {"date": date, "workflows": {}, "runs": []}
    else:
        data = {"date": date, "workflows": {}, "runs": []}

    key = workflow_id if not destination else f"{workflow_id}:{destination}"
    wf = data.setdefault("workflows", {}).setdefault(key, {})
    for k, v in (budget_used or {}).items():
        wf[k] = float(wf.get(k, 0.0)) + float(v)
    data.setdefault("runs", []).append({"run_id": run_id, "workflow_id": workflow_id, "budget_used": budget_used})

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_daily_aggregation(workspace_root: Path, date: Optional[str] = None) -> Dict[str, Any]:
    """Load daily aggregation for date (default today UTC)."""
    root = Path(workspace_root)
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = root / DAILY_AGGREGATION_DIR / DAILY_AGGREGATION_FILE.format(date=date)
    if not path.exists():
        return {"date": date, "workflows": {}, "runs": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
