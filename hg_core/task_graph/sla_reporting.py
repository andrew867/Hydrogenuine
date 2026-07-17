"""
SLA targets and reporting.

Daily and weekly rollups from run traces; success rate per primary workflow;
duplicate side-effect metric (zero target). See
hg_core/task_graph/docs/sla_reporting_spec.md.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from hg_core.task_graph.workflow_registry import get_primary_workflow_ids


def generate_daily_report(
    traces: Optional[List[Dict[str, Any]]] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Generate daily rollup from traces: runs by workflow/status, top failure
    classes, budget per workflow, side effects per destination.
    """
    traces = traces or []
    by_workflow: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "degraded": 0, "failed": 0})
    failure_counts: Dict[str, int] = defaultdict(int)
    budget_used: Dict[str, float] = defaultdict(float)
    side_effects_by_dest: Dict[str, int] = defaultdict(int)

    for t in traces:
        wf = t.get("workflow_id") or "unknown"
        status = (t.get("status") or "failed").lower()
        if status == "success":
            by_workflow[wf]["success"] += 1
        elif status == "degraded":
            by_workflow[wf]["degraded"] += 1
        else:
            by_workflow[wf]["failed"] += 1
        fc = t.get("failure_class")
        if fc:
            failure_counts[fc] += 1
        budget_used[wf] += float(t.get("budget_used") or 0)
        for dest, count in (t.get("side_effects_by_destination") or {}).items():
            side_effects_by_dest[dest] += count

    top_failures = sorted(failure_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "runs_by_workflow": dict(by_workflow),
        "by_workflow": dict(by_workflow),
        "failure_classes": dict(failure_counts),
        "top_failures": top_failures,
        "budget_used_per_workflow": dict(budget_used),
        "side_effects_per_destination": dict(side_effects_by_dest),
    }


def generate_weekly_report(
    traces: Optional[List[Dict[str, Any]]] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Generate weekly rollup from traces: success rate per primary workflow,
    duplicate side-effect incidents (zero target), regressions vs prior week.
    """
    traces = traces or []
    primary = get_primary_workflow_ids()
    per_workflow: Dict[str, Dict[str, Any]] = {}
    total_success = 0
    total_runs = len(traces)
    duplicate_side_effects = 0

    for wf in primary:
        wf_traces = [t for t in traces if t.get("workflow_id") == wf]
        n = len(wf_traces)
        success = sum(1 for t in wf_traces if (t.get("status") or "").lower() == "success")
        degraded = sum(1 for t in wf_traces if (t.get("status") or "").lower() == "degraded")
        failed = n - success - degraded
        rate = (success / n) if n else 0.0
        per_workflow[wf] = {"success": success, "degraded": degraded, "failed": failed, "success_rate": rate}
        total_success += success
        duplicate_side_effects += sum(1 for t in wf_traces if t.get("duplicate_side_effects", 0) > 0)

    overall_rate = (total_success / total_runs) if total_runs else 0.0

    return {
        "success_rate": overall_rate,
        "per_workflow": per_workflow,
        "workflows": per_workflow,
        "duplicate_side_effects": duplicate_side_effects,
        "duplicate_side_effect_incidents": duplicate_side_effects,
        "regressions_vs_prior_week": [],
    }
