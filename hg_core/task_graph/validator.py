"""
DAG validation: duplicate IDs, unknown refs, cycles, required fields, policy values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .schema import (
    DAG,
    Node,
    NODE_TYPES,
    FAILURE_MODES,
    INPUT_BINDING_MODES,
    EFFECT_CLASSES,
    LOOP_ON_BODY_FAILURE,
)


@dataclass
class ValidationResult:
    """Result of validate_dag: valid flag and list of error messages with optional path, code, suggestion."""
    valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def add_error(
        self,
        message: str,
        node_id: Optional[str] = None,
        path: Optional[str] = None,
        code: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        err: Dict[str, Any] = {"message": message}
        if node_id is not None:
            err["node_id"] = node_id
        if path is not None:
            err["path"] = path
        if code is not None:
            err["code"] = code
        if suggestion is not None:
            err["suggestion"] = suggestion
        self.errors.append(err)


def _detect_cycle(dag: DAG) -> bool:
    """True if the graph has a cycle (using DFS)."""
    node_ids = {n.id for n in dag.nodes}
    if not node_ids:
        return False

    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {nid: WHITE for nid in node_ids}

    def dfs(nid: str) -> bool:
        color[nid] = GRAY
        node = next((n for n in dag.nodes if n.id == nid), None)
        if node:
            for dep in node.depends_on:
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    return True
                if color[dep] == WHITE and dfs(dep):
                    return True
        color[nid] = BLACK
        return False

    for nid in node_ids:
        if color[nid] == WHITE and dfs(nid):
            return True
    return False


def validate_dag(dag: DAG) -> ValidationResult:
    """
    Validate a DAG before execution.

    Checks: duplicate node IDs, unknown node IDs in depends_on, cycles,
    missing required fields, invalid node type, invalid policy values,
    max_concurrency >= 1.
    """
    result = ValidationResult(valid=True)

    # Graph-level
    run_policy = dag.run_policy
    if run_policy.max_concurrency < 1:
        result.add_error(
            "run_policy.max_concurrency must be >= 1",
            path="run_policy.max_concurrency",
            code="INVALID_RUN_POLICY",
        )
    if run_policy.failure_mode not in FAILURE_MODES:
        result.add_error(
            f"run_policy.failure_mode must be one of {FAILURE_MODES}",
            path="run_policy.failure_mode",
            code="INVALID_RUN_POLICY",
        )
    if run_policy.input_binding_mode not in INPUT_BINDING_MODES:
        result.add_error(
            f"run_policy.input_binding_mode must be one of {INPUT_BINDING_MODES}",
            path="run_policy.input_binding_mode",
            code="INVALID_RUN_POLICY",
        )
    if run_policy.loop_policy_on_body_failure not in LOOP_ON_BODY_FAILURE:
        result.add_error(
            f"run_policy.loop_policy_on_body_failure must be one of {LOOP_ON_BODY_FAILURE}",
            path="run_policy.loop_policy_on_body_failure",
            code="INVALID_RUN_POLICY",
        )
    if run_policy.max_node_executions is not None and run_policy.max_node_executions < 1:
        result.add_error(
            "run_policy.max_node_executions must be >= 1",
            path="run_policy.max_node_executions",
            code="INVALID_RUN_POLICY",
        )
    if run_policy.max_total_runtime_s is not None and run_policy.max_total_runtime_s < 0:
        result.add_error(
            "run_policy.max_total_runtime_s must be non-negative",
            path="run_policy.max_total_runtime_s",
            code="INVALID_RUN_POLICY",
        )
    if run_policy.default_retry_backoff_ms is not None and run_policy.default_retry_backoff_ms < 0:
        result.add_error(
            "run_policy.default_retry_backoff_ms must be non-negative",
            path="run_policy.default_retry_backoff_ms",
            code="INVALID_RUN_POLICY",
        )

    if not dag.graph_id:
        result.add_error("graph_id is required", path="graph_id", code="MISSING_GRAPH_ID")

    # Node-level
    seen_ids: set = set()
    for node in dag.nodes:
        nid = node.id
        if not nid:
            result.add_error("node id is required", path="nodes[].id", code="MISSING_FIELD")
            continue
        if nid in seen_ids:
            result.add_error(f"duplicate node id: {nid}", node_id=nid, code="DUPLICATE_NODE_ID")
        seen_ids.add(nid)

        if node.type not in NODE_TYPES:
            result.add_error(
                f"invalid node type '{node.type}', must be one of {NODE_TYPES}",
                node_id=nid,
                path="type",
                code="INVALID_NODE_TYPE",
            )

        if not (node.assigned_entity and str(node.assigned_entity).strip()):
            result.add_error(
                "assigned_entity is required and must be non-empty",
                node_id=nid,
                path="assigned_entity",
                code="MISSING_FIELD",
            )
        if not isinstance(node.depends_on, list):
            result.add_error("depends_on must be a list", node_id=nid, path="depends_on", code="MISSING_FIELD")
        if not isinstance(node.inputs, dict):
            result.add_error("inputs must be a dict", node_id=nid, path="inputs", code="MISSING_FIELD")
        if not isinstance(node.outputs, dict):
            result.add_error("outputs must be a dict", node_id=nid, path="outputs", code="MISSING_FIELD")
        if node.policy is None:
            result.add_error("policy is required", node_id=nid, path="policy", code="MISSING_FIELD")
        if node.checkpoints is None:
            result.add_error("checkpoints is required", node_id=nid, path="checkpoints", code="MISSING_FIELD")

        for dep in node.depends_on:
            if dep not in seen_ids and not any(n.id == dep for n in dag.nodes):
                result.add_error(
                    f"depends_on references unknown node: {dep}",
                    node_id=nid,
                    path="depends_on",
                    code="UNKNOWN_DEPENDENCY",
                )

        if run_policy.strict_bindings and isinstance(node.inputs, dict):
            node_by_id = {n.id: n for n in dag.nodes}
            for inp_key, val in node.inputs.items():
                if not isinstance(val, str) or not val.startswith("$node."):
                    continue
                rest = val.replace("$node.", "", 1)
                if "." not in rest:
                    result.add_error(
                        f"input '{inp_key}' has invalid $node ref (expected $node.<node_id>.<output_key>)",
                        node_id=nid,
                        path="inputs",
                        code="MISSING_FIELD",
                    )
                    continue
                ref_nid, out_key = rest.split(".", 1)
                if ref_nid not in node_by_id:
                    result.add_error(
                        f"input '{inp_key}' references unknown node: {ref_nid}",
                        node_id=nid,
                        path="inputs",
                        code="UNKNOWN_DEPENDENCY",
                    )
                    continue
                ref_node = node_by_id[ref_nid]
                if not isinstance(ref_node.outputs, dict) or out_key not in ref_node.outputs:
                    result.add_error(
                        f"input '{inp_key}' references output '{out_key}' of node '{ref_nid}' which is not declared in that node's outputs",
                        node_id=nid,
                        path="inputs",
                        code="MISSING_FIELD",
                    )

        if node.policy is not None:
            policy = node.policy
            if policy.timeout_s is not None and policy.timeout_s < 0:
                result.add_error(
                    "policy.timeout_s must be non-negative",
                    node_id=nid,
                    path="policy.timeout_s",
                    code="INVALID_POLICY_VALUE",
                )
            if policy.max_retries < 0:
                result.add_error(
                    "policy.max_retries must be non-negative",
                    node_id=nid,
                    path="policy.max_retries",
                    code="INVALID_POLICY_VALUE",
                )
            if policy.retry_backoff_ms < 0:
                result.add_error(
                    "policy.retry_backoff_ms must be non-negative",
                    node_id=nid,
                    path="policy.retry_backoff_ms",
                    code="INVALID_POLICY_VALUE",
                )
            if policy.effect_class not in EFFECT_CLASSES:
                result.add_error(
                    f"policy.effect_class must be one of {EFFECT_CLASSES}",
                    node_id=nid,
                    path="policy.effect_class",
                    code="INVALID_POLICY_VALUE",
                )
            # Write node with retries must have idempotency_key
            if policy.effect_class == "write" and (policy.max_retries or 0) > 0:
                if not (policy.idempotency_key and str(policy.idempotency_key).strip()):
                    result.add_error(
                        "write node with max_retries > 0 must have policy.idempotency_key",
                        node_id=nid,
                        path="policy.idempotency_key",
                        code="WRITE_RETRY_NO_IDEMPOTENCY",
                        suggestion="Set policy.idempotency_key for write nodes with max_retries > 0.",
                    )
            if node.type == "loop":
                if policy.max_iterations is None:
                    result.add_error(
                        "loop node requires policy.max_iterations",
                        node_id=nid,
                        path="policy.max_iterations",
                        code="MISSING_FIELD",
                    )
                elif policy.max_iterations < 1:
                    result.add_error(
                        "policy.max_iterations must be >= 1 for loop node",
                        node_id=nid,
                        path="policy.max_iterations",
                        code="INVALID_POLICY_VALUE",
                    )

        # Control node inputs (gate, eval, loop)
        if node.type == "gate":
            inp = node.inputs or {}
            if "condition" not in inp:
                result.add_error(
                    "gate node requires inputs.condition",
                    node_id=nid,
                    path="inputs.condition",
                    code="MISSING_FIELD",
                )
            for key in ("true_targets", "false_targets"):
                if key not in inp or not isinstance(inp[key], list):
                    result.add_error(
                        f"gate node requires inputs.{key} (list of node IDs)",
                        node_id=nid,
                        path=f"inputs.{key}",
                        code="MISSING_FIELD",
                    )
            node_by_id = {n.id: n for n in dag.nodes}
            for key in ("true_targets", "false_targets"):
                if key in inp and isinstance(inp[key], list):
                    if len(inp[key]) == 0 and (not inp.get("true_targets") or not inp.get("false_targets")):
                        pass  # at least one list non-empty checked below
                    for ref_id in inp[key]:
                        if ref_id not in node_by_id:
                            result.add_error(
                                f"gate inputs.{key} references unknown node: {ref_id}",
                                node_id=nid,
                                path=f"inputs.{key}",
                                code="INVALID_GATE_TARGET",
                            )
            if isinstance(inp.get("true_targets"), list) and isinstance(inp.get("false_targets"), list):
                if len(inp["true_targets"]) == 0 and len(inp["false_targets"]) == 0:
                    result.add_error(
                        "gate must have at least one non-empty true_targets or false_targets",
                        node_id=nid,
                        path="inputs",
                        code="INVALID_GATE_TARGET",
                    )
        if node.type == "eval":
            if not isinstance(node.inputs, dict) or "expression" not in node.inputs:
                result.add_error(
                    "eval node requires inputs.expression",
                    node_id=nid,
                    path="inputs.expression",
                    code="MISSING_FIELD",
                )
        if node.type == "loop":
            inp = node.inputs or {}
            if "condition" not in inp:
                result.add_error(
                    "loop node requires inputs.condition",
                    node_id=nid,
                    path="inputs.condition",
                    code="MISSING_FIELD",
                )
            if "body" not in inp or not isinstance(inp["body"], list):
                result.add_error(
                    "loop node requires inputs.body (list of node IDs)",
                    node_id=nid,
                    path="inputs.body",
                    code="INVALID_LOOP_BODY",
                )
            else:
                node_by_id = {n.id: n for n in dag.nodes}
                for ref_id in inp["body"]:
                    if ref_id not in node_by_id:
                        result.add_error(
                            f"loop inputs.body references unknown node: {ref_id}",
                            node_id=nid,
                            path="inputs.body",
                            code="INVALID_LOOP_BODY",
                        )
                    else:
                        body_node = node_by_id[ref_id]
                        if body_node.type == "loop":
                            result.add_error(
                                "nested loops disallowed: loop body may not contain another loop node",
                                node_id=nid,
                                path="inputs.body",
                                code="NESTED_LOOP_DISALLOWED",
                            )

    # Loop body reachability and write-in-loop checkpoint (after all node IDs known)
    node_by_id = {n.id: n for n in dag.nodes}
    all_body_ids: set = set()
    loop_bodies: Dict[str, list] = {}
    for node in dag.nodes:
        if node.type == "loop" and isinstance(node.inputs.get("body"), list):
            body_ids = [x for x in node.inputs["body"] if x in node_by_id]
            loop_bodies[node.id] = body_ids
            all_body_ids.update(body_ids)
            for bid in body_ids:
                body_node = node_by_id[bid]
                for dep in body_node.depends_on:
                    if dep not in node_by_id:
                        continue
                    if dep != node.id and dep not in body_ids:
                        result.add_error(
                            f"loop body node '{bid}' may only depend on the loop node or other body nodes; "
                            f"depends_on '{dep}' is outside the loop",
                            node_id=node.id,
                            path="inputs.body",
                            code="INVALID_LOOP_BODY",
                        )
        if node.type == "loop":
            continue
        if node.id in all_body_ids and getattr(node.policy, "effect_class", "none") == "write":
            if not dag.run_policy.allow_side_effects_in_loops:
                if not (node.checkpoints and (node.checkpoints.before or node.checkpoints.after)):
                    result.add_error(
                        f"node '{node.id}' has effect_class write and is in a loop body; "
                        "require overseer checkpoint (before or after) or set run_policy.allow_side_effects_in_loops",
                        node_id=node.id,
                        path="policy.effect_class",
                        code="WRITE_IN_LOOP_BLOCKED",
                    )

    if _detect_cycle(dag):
        result.add_error("cycle detected in dependency graph", code="CYCLE_DETECTED")

    result.valid = len(result.errors) == 0
    return result
