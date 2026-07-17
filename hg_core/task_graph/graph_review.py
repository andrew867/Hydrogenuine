"""
DAG overseer review: deterministic rewrite and safety pass before execution.

Clamps run_policy and loop max_iterations; enforces checkpoints and idempotency
for write nodes; blocks write-in-loop when policy disallows.
See hg_core/task_graph/docs/dag_overseer_review_contract.md.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ReviewIssue:
    level: str  # "error" | "warn"
    code: str
    message: str
    node_id: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ReviewPolicy:
    max_iterations_cap: int = 50
    max_node_executions_cap: int = 1000
    force_fail_fast_on_write: bool = True
    allow_side_effects_in_loops: bool = False


def annotate_in_loop_body(dag_dict: Dict[str, Any]) -> None:
    """Set _meta.in_loop_body = True on each node that is in some loop's body. Mutates dag_dict."""
    nodes_by_id = {n["id"]: n for n in dag_dict.get("nodes", []) if n.get("id")}
    for node in dag_dict.get("nodes", []):
        if node.get("type") != "loop":
            continue
        body = (node.get("inputs") or {}).get("body") or []
        for bid in body:
            if bid in nodes_by_id:
                nodes_by_id[bid].setdefault("_meta", {})["in_loop_body"] = True


def review_dag(
    dag: Dict[str, Any],
    policy: ReviewPolicy,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Review and optionally rewrite DAG for safety. Call annotate_in_loop_body(dag) first if DAG has loops.

    Returns (reviewed_dag, report). reviewed_dag is None when report["blocked"] is True (any error-level issue).
    report has "blocked": bool and "issues": list of dicts with level, code, message, node_id?, suggestion?.
    """
    reviewed = copy.deepcopy(dag)
    issues: List[ReviewIssue] = []

    rp = reviewed.setdefault("run_policy", {})
    rp["max_node_executions"] = min(
        int(rp.get("max_node_executions", policy.max_node_executions_cap)),
        policy.max_node_executions_cap,
    )
    rp["allow_side_effects_in_loops"] = bool(rp.get("allow_side_effects_in_loops", False)) and policy.allow_side_effects_in_loops

    has_write = False
    for n in reviewed.get("nodes", []):
        pol = n.setdefault("policy", {})
        eff = pol.get("effect_class", "none")
        retries = int(pol.get("max_retries", 0) or 0)
        in_loop_body = bool(n.get("_meta", {}).get("in_loop_body", False))

        if n.get("type") == "loop":
            mi = int(pol.get("max_iterations", policy.max_iterations_cap) or 0)
            if mi > policy.max_iterations_cap:
                pol["max_iterations"] = policy.max_iterations_cap
                issues.append(
                    ReviewIssue(
                        "warn",
                        "CLAMP_MAX_ITERATIONS",
                        f"Clamped max_iterations to {policy.max_iterations_cap}",
                        n.get("id"),
                    )
                )

        if eff == "write":
            has_write = True
            cps = n.setdefault("checkpoints", {})
            if not cps.get("before", False):
                cps["before"] = True
                issues.append(
                    ReviewIssue("warn", "ADD_WRITE_CHECKPOINT", "Added checkpoints.before for write node", n.get("id"))
                )
            if retries > 0 and not pol.get("idempotency_key"):
                issues.append(
                    ReviewIssue(
                        "error",
                        "WRITE_RETRY_NO_IDEMPOTENCY",
                        "Write node retries require idempotency_key",
                        n.get("id"),
                    )
                )
            if in_loop_body and not policy.allow_side_effects_in_loops:
                issues.append(
                    ReviewIssue(
                        "error",
                        "WRITE_IN_LOOP_BLOCKED",
                        "Write node in loop body blocked by policy",
                        n.get("id"),
                    )
                )

    if policy.force_fail_fast_on_write and has_write:
        rp["failure_mode"] = "fail_fast"

    blocked = any(i.level == "error" for i in issues)
    report: Dict[str, Any] = {
        "blocked": blocked,
        "issues": [
            {"level": i.level, "code": i.code, "message": i.message, "node_id": i.node_id, "suggestion": i.suggestion}
            for i in issues
        ],
    }
    return (None if blocked else reviewed), report
