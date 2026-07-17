"""Swarm spawn (build child request payloads) and reduce (aggregate child outputs)."""

from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .contracts import SwarmPlan

CONTROL_GROUP_PERCENT = 10


def is_learning_control_group(correlation_id: str) -> bool:
    """
    Deterministic 10% held-out stream for learning A/B (L-track).
    Active when L3 live feedback or HG_LEARNING_CONTROL_GROUP_ENABLED is set.
    """
    try:
        from hg_learning.feedback.activation import is_control_group_enabled

        if not is_control_group_enabled():
            return False
    except ImportError:
        if os.environ.get("HG_LEARNING_CONTROL_GROUP_ENABLED", "").lower() not in (
            "1",
            "true",
            "yes",
        ):
            return False
    digest = hashlib.sha256(correlation_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < CONTROL_GROUP_PERCENT


def swarm_spawn(
    *,
    plan: SwarmPlan,
    correlation_id: str,
    learning_control_group: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Build child request payloads (capped by plan.max_children). Caller launches via DagLauncher."""
    from .contracts import MAX_SWARM_CHILDREN

    if learning_control_group is None:
        learning_control_group = is_learning_control_group(correlation_id)
    cap = min(plan.max_children, MAX_SWARM_CHILDREN)
    tasks = plan.tasks[:cap]
    out: List[Dict[str, Any]] = []
    for t in tasks:
        out.append({
            "child_request_id": str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "workflow_id": t.get("workflow_id"),
            "inputs": t.get("inputs", {}),
            "budgets": {
                "max_tool_calls": plan.max_tool_calls_per_child,
                "max_wall_clock_s": plan.max_wall_clock_s_per_child,
            },
            "learning_control_group": learning_control_group,
            "learning_priors_enabled": not learning_control_group,
        })
    return out


def swarm_reduce(*, child_outputs: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], List[str]]:
    """Aggregate child outputs into summary, artifacts, warnings. Returns (summary, artifacts, warnings)."""
    artifacts: Dict[str, Any] = {"child_count": len(child_outputs)}
    if child_outputs:
        first = child_outputs[0]
        cg = bool(first.get("learning_control_group"))
        artifacts["learning_control_group"] = cg
        artifacts["learning_priors_enabled"] = bool(first.get("learning_priors_enabled", not cg))
        artifacts["correlation_id"] = first.get("correlation_id")
        try:
            from hg_learning.feedback.control_group import (
                default_control_group_store,
                record_swarm_learning_run,
            )
            from hg_learning.flywheel.corpus_store import default_corpus_store

            cid = str(first.get("correlation_id") or "unknown")
            priors = bool(artifacts["learning_priors_enabled"])
            store = default_control_group_store()
            store.record_run(
                correlation_id=cid,
                in_control_group=cg,
                priors_enabled=priors,
                details={"child_count": len(child_outputs)},
            )
            store.close()
            record_swarm_learning_run(
                default_corpus_store(),
                correlation_id=cid,
                in_control_group=cg,
                priors_enabled=priors,
                child_count=len(child_outputs),
            )
        except Exception:
            pass
    return (
        f"Reduced {len(child_outputs)} child outputs",
        artifacts,
        [],
    )
