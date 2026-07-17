"""
Task graph executor: validate, run loop, readiness, binding, retry/failure, persistence, telemetry.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from collections import deque

from .schema import DAG, Node, load_dag
from .validator import validate_dag, ValidationResult
from .state_machine import NodeStatus, can_transition
from .state_store import RunState, StateStore
from .state_history import write_snapshot as state_history_write_snapshot
from .dispatch import dispatch_node, make_tool_contract_dispatcher
from .recording import build_canonical_request
from .budget_enforcer import (
    BUDGET_EXCEEDED_CODE,
    apply_after_dispatch,
    check_before_dispatch,
)
from .telemetry import default_telemetry_sink
from .tool_adapter_contract import ToolAdapter
from .tool_registry import ToolRegistry
from .expression import evaluate as evaluate_expression
from .failure_classification import classify_failure, failure_class_from_error_dict
from .cancel import is_cancel_requested

logger = logging.getLogger(__name__)

try:
    from hg_realtime.steering import check_steering as _check_steering
except ImportError:
    _check_steering = None

try:
    from hg_core.scope_context import scope_context
except ImportError:
    def scope_context(scope_type: str, scope_id: str, **kwargs):  # noqa: D103
        from contextlib import nullcontext
        return nullcontext()


def _ledger_workspace_root(run_dir: Optional[Path] = None) -> Optional[Path]:
    """Resolve workspace root for ledger emit (best-effort)."""
    if run_dir is not None:
        # run_dir is often memory/automation/dag_runs/<id> or similar under workspace
        p = Path(run_dir)
        for _ in range(5):
            if (p / "memory").is_dir():
                return p
            p = p.parent
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except ImportError:
        return None


def _ledger_emit_run_lifecycle(workspace_root: Optional[Path], run_id: str, phase: str) -> None:
    """Emit RUN_START or RUN_END to canonical ledger (best-effort, never raise)."""
    if workspace_root is None:
        return
    try:
        from hg_core.ledger import emit
        emit(
            "RUN_START" if phase == "start" else "RUN_END",
            "run",
            run_id,
            {"phase": phase, "graph_id": ""},
            scope={"type": "run", "id": run_id},
            workspace_root=workspace_root,
        )
    except Exception:
        logger.debug("Ledger run lifecycle emit failed (non-fatal)", exc_info=True)


def _ensure_run_state_initialized(
    run_state: RunState,
    graph_inputs: Dict[str, Any],
    run_dir: Optional[Path],
) -> None:
    """Set default run_state.state values when missing so DAG runs have sufficient initialization.
    Ensures: _stakes_trust_band, budget_used, _escrow_locked, run_config. Reduces repeated .get() and
    avoids inconsistent shape across stakes gating, budget, summary, and repr_interp.
    """
    if run_dir is None:
        return
    import os
    state = run_state.state
    # Stakes: default trust band for runs without prior analysis (from run_config or env)
    if "_stakes_trust_band" not in state:
        _rc = (graph_inputs or {}).get("run_config")
        _default_band = None
        if isinstance(_rc, dict) and "default_trust_band" in _rc:
            _default_band = _rc.get("default_trust_band")
        if _default_band is None:
            _default_band = os.environ.get("HG_DAG_DEFAULT_TRUST_BAND", "2")
        try:
            state["_stakes_trust_band"] = int(_default_band)
        except (TypeError, ValueError):
            state["_stakes_trust_band"] = 2
    # Budget: ensure dict so check_before_dispatch/summary/telemetry see consistent shape
    if "budget_used" not in state:
        state["budget_used"] = {}
    # Escrow: explicit zero so stakes gating and ledger use same key
    if "_escrow_locked" not in state:
        state["_escrow_locked"] = 0.0
    # Run config: mirror from graph_inputs so run_state_dict.get("run_config") works everywhere
    if "run_config" not in state and graph_inputs:
        _rc = graph_inputs.get("run_config")
        if _rc is not None and isinstance(_rc, dict):
            state["run_config"] = dict(_rc)


def _get_stakes_context(run_state_dict: Dict[str, Any]) -> Tuple[float, int, float]:
    """Return (budget_used_sum, trust_band, escrow_locked) from run state for stakes gating. Single place for shape."""
    budget_used = run_state_dict.get("budget_used") or {}
    budget_sum = sum(float(v) for v in (budget_used if isinstance(budget_used, dict) else {}).values())
    trust_band = int(run_state_dict.get("_stakes_trust_band", 0))
    escrow_locked = float(run_state_dict.get("_escrow_locked", 0) or 0)
    return budget_sum, trust_band, escrow_locked


# Node type -> action for stakes gating (single definition, used in main loop and resume loop)
_NODE_TYPE_TO_ACTION: Dict[str, str] = {
    "agent": "DECISION_PROPOSED",
    "tool": "WRITE",
    "eval": "READ",
    "gate": "READ",
    "transform": "WRITE",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _repr_interp_capture_after_node(
    workspace_root: Optional[Path],
    run_id: str,
    run_dir: Optional[Path],
    run_state_dict: Dict[str, Any],
    nid: str,
    node_type: str,
    graph_id: str,
) -> None:
    """Layer 8 Phase 2: opt-in repr_interp capture after node completion (no-op if disabled)."""
    if workspace_root is None or run_dir is None:
        return
    try:
        from hg_core.repr_interp.capture import is_repr_interp_capture_enabled, capture_context
        if is_repr_interp_capture_enabled(workspace_root, run_state_dict.get("run_config")):
            capture_context(
                workspace_root,
                run_id,
                run_dir,
                nid,
                node_type,
                context_ref={"run_id": run_id, "node_id": nid, "graph_id": graph_id},
            )
    except Exception:
        logger.debug("repr_interp capture after node failed (non-fatal)", exc_info=True)


def _as_epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        try:
            normalized = text.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _successors_by_id(nodes: List[Node]) -> Dict[str, List[str]]:
    """Reverse dependency graph: succ[nid] = list of node ids that have nid in depends_on (successors)."""
    rev: Dict[str, List[str]] = {n.id: [] for n in nodes}
    for node in nodes:
        for dep in node.depends_on:
            if dep in rev:
                rev[dep].append(node.id)
    return rev


def _reachable_from(seeds: List[str], successors: Dict[str, List[str]]) -> set:
    """BFS from seeds following successors. Deterministic: use sorted order for frontier."""
    out: set = set()
    q: deque = deque(sorted(seeds))
    while q:
        nid = q.popleft()
        if nid in out:
            continue
        out.add(nid)
        for s in sorted(successors.get(nid, [])):
            if s not in out:
                q.append(s)
    return out


def _propagate_deps_all_skipped(nodes: List[Node], skipped: set) -> None:
    """Mark SKIPPED any node that is PENDING/READY and has all deps in skipped. Repeat until fixpoint."""
    by_id = {n.id: n for n in nodes}
    while True:
        changed = False
        for node in sorted(nodes, key=lambda n: n.id):
            s = node.status or NodeStatus.PENDING.value
            if s not in (NodeStatus.PENDING.value, NodeStatus.READY.value):
                continue
            if not node.depends_on:
                continue
            if all(dep in skipped for dep in node.depends_on):
                node.status = NodeStatus.SKIPPED.value
                skipped.add(node.id)
                changed = True
        if not changed:
            break


def _body_to_loop_map(dag: DAG) -> Dict[str, str]:
    """Return map body_node_id -> loop_id for each node that is in some loop's body."""
    out: Dict[str, str] = {}
    for node in dag.nodes:
        if node.type == "loop" and isinstance(node.inputs, dict):
            body = node.inputs.get("body") or []
            for bid in body:
                out[bid] = node.id
    return out


def _reset_loop_body_nodes(
    nodes: List[Node],
    by_id: Dict[str, Node],
    body_ids: List[str],
    run_state: RunState,
) -> None:
    """Reset body nodes for next iteration: PENDING, clear error/started_at/ended_at, attempt_count=0, clear node_outputs."""
    for bid in body_ids:
        if bid not in by_id:
            continue
        n = by_id[bid]
        n.status = NodeStatus.PENDING.value
        n.error = None
        n.started_at = None
        n.ended_at = None
        n.attempt_count = 0
        run_state.node_outputs.pop(bid, None)


def _get_loop_body_complete(
    dag: DAG,
    nodes: List[Node],
    run_state: RunState,
) -> Optional[Tuple[str, List[str]]]:
    """If there is an active loop whose body is all DONE or SKIPPED, return (loop_id, body_ids)."""
    by_id = {n.id: n for n in nodes}
    for loop_id, lstate in (run_state.loop_state or {}).items():
        if not lstate.get("active"):
            continue
        loop_node = by_id.get(loop_id)
        if not loop_node or loop_node.type != "loop":
            continue
        body_ids = list((loop_node.inputs or {}).get("body") or [])
        if not body_ids:
            continue
        if all(
            by_id.get(bid) and (by_id[bid].status == NodeStatus.DONE.value or by_id[bid].status == NodeStatus.SKIPPED.value)
            for bid in body_ids
        ):
            return (loop_id, body_ids)
    return None


def _control_payload(nid: str, body_to_loop: Dict[str, str], run_state: RunState) -> Dict[str, Any]:
    """Return extra telemetry fields when node is in a loop body: loop_id, iteration, control_parent."""
    if nid not in body_to_loop:
        return {}
    loop_id = body_to_loop[nid]
    lstate = (run_state.loop_state or {}).get(loop_id) or {}
    return {
        "loop_id": loop_id,
        "iteration": lstate.get("iteration"),
        "control_parent": loop_id,
    }


def _advance_loop(
    dag: DAG,
    nodes: List[Node],
    run_state: RunState,
    graph_inputs: Dict[str, Any],
    loop_info: Tuple[str, List[str]],
    by_id: Dict[str, Node],
) -> None:
    """Re-evaluate loop condition; either start next iteration (reset body) or set loop inactive."""
    loop_id, body_ids = loop_info
    loop_node = by_id.get(loop_id)
    if not loop_node or loop_node.type != "loop":
        return
    lstate = run_state.loop_state.setdefault(loop_id, {})
    current = lstate.get("iteration", 0)
    max_iterations = lstate.get("max_iterations", 1)
    next_iter = current + 1
    if next_iter > max_iterations:
        lstate["active"] = False
        lstate["iteration"] = current
        return
    context = {
        "state": run_state.state,
        "node": run_state.node_outputs,
        "graph": {"inputs": graph_inputs},
        "loop": {
            "id": loop_id,
            "iteration": next_iter,
            "max_iterations": max_iterations,
            "state": run_state.state.get("loops", {}).get(loop_id, {}),
        },
    }
    expression_strict = getattr(dag.run_policy, "expression_strict_mode", False)
    condition_value = False
    try:
        condition_value = bool(evaluate_expression(
            (loop_node.inputs or {}).get("condition"),
            context,
            strict=expression_strict,
        ))
    except Exception:
        condition_value = False
    lstate["last_condition_value"] = condition_value
    if not condition_value:
        lstate["active"] = False
        lstate["iteration"] = current
        return
    lstate["iteration"] = next_iter
    lstate["iteration_started_at"] = datetime.now(timezone.utc).timestamp()
    _reset_loop_body_nodes(nodes, by_id, body_ids, run_state)


def topological_order(dag: DAG) -> List[str]:
    """Return node IDs in topological order (deterministic: lexical by id when multiple choices)."""
    in_degree = {n.id: len(n.depends_on) for n in dag.nodes}
    rev: Dict[str, List[str]] = {n.id: [] for n in dag.nodes}
    for node in dag.nodes:
        for dep in node.depends_on:
            if dep in rev:
                rev[dep].append(node.id)
    q: deque = deque(nid for nid, d in in_degree.items() if d == 0)
    order: List[str] = []
    while q:
        batch = sorted(q)
        q.clear()
        for nid in batch:
            order.append(nid)
            for j in rev.get(nid, []):
                in_degree[j] -= 1
                if in_degree[j] == 0:
                    q.append(j)
    return order


_TERMINAL_NODE_STATUSES = frozenset({
    NodeStatus.DONE.value,
    NodeStatus.FAILED.value,
    NodeStatus.SKIPPED.value,
    NodeStatus.BLOCKED.value,
})


def compute_final_run_status(nodes: List[Node], failure_mode: str) -> str:
    """Derive run final_status; incomplete graphs are partial, not completed."""
    any_failed = any(n.status == NodeStatus.FAILED.value for n in nodes)
    any_incomplete = any((n.status or NodeStatus.PENDING.value) not in _TERMINAL_NODE_STATUSES for n in nodes)
    if any_failed:
        return "failed" if failure_mode == "fail_fast" else "partial"
    if any_incomplete:
        return "partial"
    return "completed"


def get_ready_nodes(dag: DAG, nodes: List[Node], failure_mode: str) -> List[str]:
    """
    Return node IDs that are ready to run: all deps done, self is pending or ready,
    and not skipped due to upstream failure under continue mode.
    Propagates "deps all SKIPPED -> SKIPPED" so no node stays ready when all its deps are skipped.
    """
    by_id = {n.id: n for n in nodes}
    done = {n.id for n in nodes if n.status == NodeStatus.DONE.value}
    failed = {n.id for n in nodes if n.status == NodeStatus.FAILED.value}
    skipped = {n.id for n in nodes if n.status == NodeStatus.SKIPPED.value}
    _propagate_deps_all_skipped(nodes, skipped)

    def upstream_failed(nid: str) -> bool:
        node = by_id.get(nid)
        if not node:
            return False
        return any(dep in failed for dep in node.depends_on)

    ready: List[str] = []
    for node in nodes:
        s = node.status or NodeStatus.PENDING.value
        if s not in (NodeStatus.PENDING.value, NodeStatus.READY.value):
            continue
        if s == NodeStatus.BLOCKED.value or s == NodeStatus.SKIPPED.value:
            continue
        if not all(dep in done for dep in node.depends_on):
            continue
        if failure_mode == "continue" and upstream_failed(node.id):
            continue
        ready.append(node.id)
    return sorted(ready)


def _extract_dispatch_error(output: Dict[str, Any]) -> Dict[str, Any]:
    """Pull a structured error from dispatcher/tool output (top-level or nested result)."""
    err = output.get("error")
    if isinstance(err, dict) and (err.get("message") or err.get("code")):
        return err
    if isinstance(err, str) and err.strip():
        return {"code": "DISPATCH_FAILED", "message": err.strip()}
    outputs = output.get("outputs")
    if isinstance(outputs, dict):
        result = outputs.get("result")
        if isinstance(result, dict):
            message = result.get("message") or result.get("error")
            if message:
                code = result.get("error") if isinstance(result.get("error"), str) else "DISPATCH_FAILED"
                if isinstance(code, str) and code == str(message):
                    code = "DISPATCH_FAILED"
                return {"code": str(code or "DISPATCH_FAILED"), "message": str(message)}
    return {"code": "DISPATCH_FAILED", "message": "dispatch failed"}


def resolve_inputs(
    node: Node,
    node_outputs: Dict[str, Dict[str, Any]],
    graph_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Resolve node inputs: $graph.inputs.* and $node.<id>.* to concrete values.
    Returns dict of key -> value. Unresolved refs are left as strings (caller can block or error).
    """
    resolved: Dict[str, Any] = {}
    for key, val in node.inputs.items():
        if isinstance(val, str) and val.startswith("$graph.inputs."):
            path = val.replace("$graph.inputs.", "")
            if path in graph_inputs:
                resolved[key] = graph_inputs.get(path)
            else:
                resolved[key] = ""
        elif isinstance(val, str) and val.startswith("$node."):
            # $node.<node_id>.<output_key>
            rest = val.replace("$node.", "")
            if "." in rest:
                nid, out_key = rest.split(".", 1)
                outputs = node_outputs.get(nid, {})
                if out_key in outputs:
                    resolved[key] = outputs.get(out_key)
                elif out_key == "result" and outputs:
                    resolved[key] = outputs
                else:
                    resolved[key] = val
            else:
                resolved[key] = val
        else:
            resolved[key] = val
    return resolved


class TaskGraphExecutor:
    """
    Execute a predefined DAG: validate, schedule ready nodes, dispatch, retry/failure, persist, telemetry.
    """

    def __init__(
        self,
        dispatcher: Optional[Callable[[Node, Dict[str, Any]], Dict[str, Any]]] = None,
        overseer: Optional[Any] = None,
        state_store: Optional[StateStore] = None,
        telemetry: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        recorder: Optional[Any] = None,
        tool_registry: Optional[ToolRegistry] = None,
        tool_adapter: Optional[ToolAdapter] = None,
        rate_limiter: Optional[Any] = None,
    ):
        base_dispatcher = dispatcher or dispatch_node
        if tool_registry and tool_adapter:
            self.dispatcher = make_tool_contract_dispatcher(
                tool_registry,
                tool_adapter,
                base_dispatcher=base_dispatcher,
                rate_limiter=rate_limiter,
            )
        else:
            self.dispatcher = base_dispatcher
        self.overseer = overseer
        self.state_store = state_store or StateStore()
        self.telemetry = telemetry or default_telemetry_sink(overseer=overseer)
        self.recorder = recorder
        self.tool_registry = tool_registry
        self.tool_adapter = tool_adapter

    def run(
        self,
        dag: DAG,
        graph_inputs: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        run_dir: Optional[Path] = None,
        reviewed_dag: Optional[Dict[str, Any]] = None,
        review_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validate and execute the DAG to completion.
        Returns run summary with final_status, node statuses, and any error.
        When run_dir is set, writes graph.json, state.json, summary.json, events.jsonl there.
        When run_dir and reviewed_dag and review_report are set, writes graph.reviewed.json and
        review_report.json and runs the reviewed DAG (validated) instead of the input dag.
        """
        # Always apply DAG-declared defaults, then overlay caller-provided inputs.
        # This prevents unresolved $graph.inputs.* refs when callers provide only
        # a partial input set.
        graph_inputs = {**dict(dag.inputs), **(graph_inputs or {})}
        result = validate_dag(dag)
        if not result.valid:
            return {
                "ok": False,
                "run_id": run_id,
                "error": "validation_failed",
                "validation_errors": result.errors,
            }
        run_id = run_id or str(uuid.uuid4())
        nodes = list(dag.nodes)
        for n in nodes:
            n.status = NodeStatus.PENDING.value
            n.attempt_count = 0
            n.started_at = None
            n.ended_at = None
            n.error = None

        run_state = RunState(
            run_id=run_id,
            graph_id=dag.graph_id,
            started_at=_iso_now(),
            updated_at=_iso_now(),
            node_outputs={},
            node_states={},
        )

        if run_dir is not None:
            run_dir = Path(run_dir)
            run_dir.mkdir(parents=True, exist_ok=True)
            graph_path = run_dir / "graph.json"
            graph_path.write_text(
                json.dumps(dag.to_dict(), indent=2), encoding="utf-8"
            )
            try:
                from hg_core.ledger import emit_artifact_published, emit_retrieval_set
                _ws = _ledger_workspace_root(run_dir)
                if _ws is not None:
                    emit_artifact_published(
                        str(graph_path),
                        artifact_type="graph",
                        scope={"type": "run", "id": run_id},
                        workspace_root=_ws,
                    )
                    emit_retrieval_set(
                        top_k_ids=[n.id for n in nodes],
                        agent_id=dag.graph_id or "dag",
                        scope={"type": "run", "id": run_id},
                        workspace_root=_ws,
                    )
            except Exception:
                pass
            if reviewed_dag is not None and review_report is not None:
                (run_dir / "graph.reviewed.json").write_text(
                    json.dumps(reviewed_dag, indent=2), encoding="utf-8"
                )
                (run_dir / "review_report.json").write_text(
                    json.dumps(review_report, indent=2), encoding="utf-8"
                )
                dag = DAG.from_dict(reviewed_dag)
                result = validate_dag(dag)
                if not result.valid:
                    return {
                        "ok": False,
                        "run_id": run_id,
                        "error": "validation_failed",
                        "validation_errors": result.errors,
                    }
                nodes = list(dag.nodes)
                for n in nodes:
                    n.status = NodeStatus.PENDING.value
                    n.attempt_count = 0
                    n.started_at = None
                    n.ended_at = None
                    n.error = None
                run_state.graph_id = dag.graph_id
            events_path = run_dir / "events.jsonl"
            behavior_events_path = run_dir / "behavior_events.jsonl"
            orig_telemetry = self.telemetry
            _ws_root = _ledger_workspace_root(run_dir)
            with open(events_path, "a", encoding="utf-8") as events_file:
                def run_dir_telemetry(event_name: str, payload: Dict[str, Any]) -> None:
                    orig_telemetry(event_name, payload)
                    events_file.write(json.dumps({"event": event_name, **payload}) + "\n")
                    events_file.flush()
                    if event_name == "dag_node_started":
                        from . import behavior_telemetry as _bt
                        ev = _bt.make_behavior_event(
                            run_id=payload.get("run_id", ""),
                            workflow_id=payload.get("graph_id", ""),
                            work_item_id=payload.get("node_id", ""),
                            event_type="delegation.assign",
                            agent_id=payload.get("assigned_entity") or "",
                        )
                        try:
                            with open(behavior_events_path, "a", encoding="utf-8") as bf:
                                bf.write(json.dumps(ev) + "\n")
                                bf.flush()
                        except Exception:
                            pass
                self.telemetry = run_dir_telemetry
                try:
                    self.telemetry("dag_run_started", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                    })
                    with scope_context(scope_type="run", scope_id=run_id, run_id=run_id):
                        _ledger_emit_run_lifecycle(_ws_root, run_id, "start")
                        try:
                            return self._run_loop(
                                dag, nodes, run_id, run_state, graph_inputs,
                                by_id={n.id: n for n in nodes},
                                body_to_loop=_body_to_loop_map(dag),
                                run_dir=run_dir,
                            )
                        finally:
                            _ledger_emit_run_lifecycle(_ws_root, run_id, "end")
                finally:
                    self.telemetry = orig_telemetry
        else:
            _ws_root = _ledger_workspace_root(None)
            self.telemetry("dag_run_started", {
                "graph_id": dag.graph_id,
                "run_id": run_id,
            })
            by_id = {n.id: n for n in nodes}
            body_to_loop = _body_to_loop_map(dag)
            with scope_context(scope_type="run", scope_id=run_id, run_id=run_id):
                _ledger_emit_run_lifecycle(_ws_root, run_id, "start")
                try:
                    return self._run_loop(
                        dag, nodes, run_id, run_state, graph_inputs,
                        by_id, body_to_loop, run_dir=None,
                    )
                finally:
                    _ledger_emit_run_lifecycle(_ws_root, run_id, "end")

    def _run_loop(
        self,
        dag: DAG,
        nodes: List[Node],
        run_id: str,
        run_state: RunState,
        graph_inputs: Dict[str, Any],
        by_id: Dict[str, Node],
        body_to_loop: Dict,
        run_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute the main run loop (with run scope already set)."""
        _ensure_run_state_initialized(run_state, graph_inputs, run_dir)
        # Load stakes policy once per run to avoid repeated file I/O on every node
        _ws_root_run = _ledger_workspace_root(run_dir) if run_dir else None
        _stakes_policy_run: Optional[Dict[str, Any]] = None
        if _ws_root_run is not None:
            try:
                from hg_core.stakes import load_policy as _load_stakes_policy
                _stakes_policy_run = _load_stakes_policy(_ws_root_run)
            except Exception:
                pass
        max_concurrency = dag.run_policy.max_concurrency
        failure_mode = dag.run_policy.failure_mode
        max_node_executions = getattr(dag.run_policy, "max_node_executions", None)
        execution_count = 0

        while True:
            if _check_steering is not None and run_dir is not None:
                try:
                    action, inject_payload = _check_steering(run_id, run_dir)
                    if action == "inject" and inject_payload is not None:
                        run_state.state["_steering_inject"] = inject_payload
                except Exception as e:  # noqa: BLE001
                    logger.debug("check_steering failed: %s", e)
            cancel_requested, cancel_payload = is_cancel_requested(run_dir)
            if cancel_requested:
                return self._handle_cancel(run_id, dag, nodes, run_state, run_dir, cancel_payload)
            runtime_summary = self._check_runtime_cap(dag, run_id, nodes, run_state, run_dir)
            if runtime_summary is not None:
                return runtime_summary
            ready = get_ready_nodes(dag, nodes, failure_mode)
            if max_node_executions is not None and execution_count >= max_node_executions:
                run_state.final_status = "failed"
                run_state.updated_at = _iso_now()
                run_state.state["_run_error"] = {
                    "code": "MAX_NODE_EXECUTIONS_EXCEEDED",
                    "message": f"max_node_executions cap ({max_node_executions}) exceeded",
                }
                run_state.node_states = {n.id: n.to_dict() for n in nodes}
                self.state_store.save(run_state, nodes)
                if run_dir is not None:
                    self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
                self.telemetry("dag_run_completed", {
                    "graph_id": dag.graph_id,
                    "run_id": run_id,
                    "final_status": run_state.final_status,
                })
                return self._summary(dag, nodes, run_id, run_state, ok=False)
            if not ready:
                running = [n for n in nodes if n.status == NodeStatus.RUNNING.value]
                if running:
                    break
                if failure_mode == "continue":
                    for n in nodes:
                        if n.status == NodeStatus.PENDING.value and any(
                            by_id.get(dep) and by_id[dep].status == NodeStatus.FAILED.value for dep in n.depends_on
                        ):
                            n.status = NodeStatus.SKIPPED.value
                            self.telemetry("dag_node_skipped", {
                                "graph_id": dag.graph_id,
                                "run_id": run_id,
                                "node_id": n.id,
                            })
                    ready = get_ready_nodes(dag, nodes, failure_mode)
                    if not ready:
                        loop_info = _get_loop_body_complete(dag, nodes, run_state)
                        if loop_info:
                            _advance_loop(dag, nodes, run_state, graph_inputs, loop_info, by_id)
                            continue
                        break
                    continue
                loop_info = _get_loop_body_complete(dag, nodes, run_state)
                if loop_info:
                    _advance_loop(dag, nodes, run_state, graph_inputs, loop_info, by_id)
                    continue
                break

            to_run = ready[:max_concurrency]
            for nid in to_run:
                node = by_id[nid]
                current = node.status or NodeStatus.PENDING.value
                if current == NodeStatus.PENDING.value:
                    node.status = NodeStatus.READY.value
                    current = NodeStatus.READY.value
                if not can_transition(current, NodeStatus.RUNNING.value):
                    continue
                node.status = NodeStatus.RUNNING.value
                execution_count += 1
                node.error = None  # clear so retry attempt starts fresh
                node.started_at = _iso_now()
                node.attempt_count = node.attempt_count + 1
                self.telemetry("dag_node_started", {
                    "graph_id": dag.graph_id,
                    "run_id": run_id,
                    "node_id": nid,
                    "node_type": node.type,
                    "assigned_entity": node.assigned_entity,
                    "attempt_count": node.attempt_count,
                    **_control_payload(nid, body_to_loop, run_state),
                })

                # Gate: evaluate condition, propagate skip (R_skipped - R_taken), mark gate DONE without dispatch
                if node.type == "gate":
                    condition_value = False
                    try:
                        context = {
                            "state": run_state.state,
                            "node": run_state.node_outputs,
                            "graph": {"inputs": graph_inputs},
                            "loop": {},
                        }
                        expression_strict = getattr(dag.run_policy, "expression_strict_mode", False)
                        condition_value = bool(evaluate_expression(
                            (node.inputs or {}).get("condition"),
                            context,
                            strict=expression_strict,
                        ))
                    except Exception:
                        condition_value = False
                    inp = node.inputs or {}
                    true_targets = list(inp.get("true_targets") or [])
                    false_targets = list(inp.get("false_targets") or [])
                    taken = true_targets if condition_value else false_targets
                    non_taken = false_targets if condition_value else true_targets
                    succ = _successors_by_id(nodes)
                    R_taken = _reachable_from(taken, succ) if taken else set()
                    R_skipped = _reachable_from(non_taken, succ) if non_taken else set()
                    to_skip = sorted(R_skipped - R_taken)
                    skipped_ids = {n.id for n in nodes if n.status == NodeStatus.SKIPPED.value}
                    for sid in to_skip:
                        if sid in by_id and by_id[sid].status not in (
                            NodeStatus.DONE.value,
                            NodeStatus.FAILED.value,
                            NodeStatus.SKIPPED.value,
                        ):
                            by_id[sid].status = NodeStatus.SKIPPED.value
                            skipped_ids.add(sid)
                            self.telemetry("dag_node_skipped", {
                                "graph_id": dag.graph_id,
                                "run_id": run_id,
                                "node_id": sid,
                                "gate_id": nid,
                                "gate_taken": condition_value,
                            })
                    _propagate_deps_all_skipped(nodes, skipped_ids)
                    node.status = NodeStatus.DONE.value
                    node.ended_at = _iso_now()
                    run_state.node_outputs[nid] = {"taken": condition_value}
                    self.telemetry("dag_node_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "node_id": nid,
                        "status": node.status,
                        "attempt_count": node.attempt_count,
                        "duration_ms": 0,
                        "gate_taken": condition_value,
                    })
                    if node.checkpoints.after and self.overseer:
                        try:
                            self.overseer.checkpoint_after(node, run_state)
                        except Exception:
                            pass
                    if self._should_pause(dag, node, "after"):
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        summary = self._summary(dag, nodes, run_id, run_state, ok=True)
                        return {**summary, "status": "paused", "checkpoint": {"node_id": nid, "position": "after"}}
                    self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                    continue

                # Loop: evaluate condition once, init loop_state, optionally run first iteration (reset body), mark loop DONE
                if node.type == "loop":
                    body_ids = list((node.inputs or {}).get("body") or [])
                    max_iterations = getattr(node.policy, "max_iterations", None) or 1
                    run_state.state.setdefault("loops", {})[node.id] = run_state.state.get("loops", {}).get(node.id, {})
                    lstate = run_state.loop_state.setdefault(node.id, {})
                    now_ts = datetime.now(timezone.utc).timestamp()
                    lstate["iteration"] = 0
                    lstate["active"] = True
                    lstate["max_iterations"] = max_iterations
                    lstate["iteration_started_at"] = now_ts
                    context = {
                        "state": run_state.state,
                        "node": run_state.node_outputs,
                        "graph": {"inputs": graph_inputs},
                        "loop": {
                            "id": node.id,
                            "iteration": 1,
                            "max_iterations": max_iterations,
                            "state": run_state.state.get("loops", {}).get(node.id, {}),
                        },
                    }
                    expression_strict = getattr(dag.run_policy, "expression_strict_mode", False)
                    condition_value = False
                    try:
                        condition_value = bool(evaluate_expression(
                            (node.inputs or {}).get("condition"),
                            context,
                            strict=expression_strict,
                        ))
                    except Exception:
                        condition_value = False
                    lstate["last_condition_value"] = condition_value
                    if not condition_value:
                        lstate["active"] = False
                        node.status = NodeStatus.DONE.value
                        node.ended_at = _iso_now()
                        run_state.node_outputs[nid] = {}
                        self.telemetry("dag_node_completed", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "status": node.status,
                            "attempt_count": node.attempt_count,
                            "duration_ms": 0,
                        })
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        continue
                    lstate["iteration"] = 1
                    _reset_loop_body_nodes(nodes, by_id, body_ids, run_state)
                    node.status = NodeStatus.DONE.value
                    node.ended_at = _iso_now()
                    run_state.node_outputs[nid] = {"iteration": 1}
                    self.telemetry("dag_node_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "node_id": nid,
                        "status": node.status,
                        "attempt_count": node.attempt_count,
                        "duration_ms": 0,
                        "loop_id": nid,
                        "iteration": 1,
                    })
                    self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                    continue

                # Steering: before_node (before checkpoint_before)
                if self.overseer and hasattr(self.overseer, "before_node"):
                    try:
                        _steering_ret = self.overseer.before_node(node, run_state)
                        if isinstance(_steering_ret, dict) and _steering_ret.get("block"):
                            _reason = _steering_ret.get("reason") or "steering blocked"
                            node.status = NodeStatus.BLOCKED.value
                            node.error = {"code": "STEERING_BLOCKED", "reason": _reason}
                            node.ended_at = _iso_now()
                            if hasattr(self.overseer, "after_node"):
                                try:
                                    self.overseer.after_node(
                                        node,
                                        run_state,
                                        {"ok": False, "error": {"code": "STEERING_BLOCKED", "reason": _reason}},
                                    )
                                except Exception:
                                    pass
                            self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                            continue
                    except Exception:
                        pass

                if node.checkpoints.before and self.overseer:
                    try:
                        self.overseer.checkpoint_before(node, run_state)
                    except Exception:
                        pass

                inputs = resolve_inputs(node, run_state.node_outputs, graph_inputs)
                unresolved = [k for k, v in inputs.items() if isinstance(v, str) and v.startswith("$")]
                input_binding_mode = dag.run_policy.input_binding_mode
                output = None

                if unresolved:
                    if input_binding_mode == "strict":
                        node.error = {"code": "INPUT_RESOLUTION_ERROR", "message": f"Unresolved ref(s): {unresolved}"}
                    elif input_binding_mode == "blocked":
                        node.status = NodeStatus.BLOCKED.value
                        node.error = None
                        node.ended_at = _iso_now()
                        self.telemetry("dag_node_blocked", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "unresolved": unresolved,
                        })
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        continue  # skip dispatcher and output handling for this node
                    # lenient: pass inputs as-is, fall through to dispatcher

                run_state.body_to_loop = body_to_loop
                rec_token = None
                if self.recorder and run_dir is not None:
                    ctrl = _control_payload(nid, body_to_loop, run_state)
                    request = build_canonical_request(node, inputs)
                    rec_token = self.recorder.record_request(
                        node_id=nid,
                        attempt_no=node.attempt_count,
                        request=request,
                        loop_id=ctrl.get("loop_id"),
                        iteration=ctrl.get("iteration"),
                    )

                # Budget: before dispatch check
                run_policy_dict = dag.run_policy.to_dict()
                run_state_dict = run_state.state
                cost = {"dispatch_attempts": 1}
                allowed, budget_err = check_before_dispatch(run_policy_dict, run_state_dict, cost)
                if not allowed and budget_err is not None:
                    run_state.final_status = "failed"
                    run_state.updated_at = _iso_now()
                    run_state.state["_run_error"] = budget_err
                    run_state.node_states = {n.id: n.to_dict() for n in nodes}
                    self.state_store.save(run_state, nodes)
                    self.telemetry("budget_exceeded", dict(budget_err))
                    if run_dir is not None:
                        self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
                    self.telemetry("dag_run_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "final_status": run_state.final_status,
                    })
                    return self._summary(dag, nodes, run_id, run_state, ok=False)

                # Stakes gating (Ch1.5): check_gate before dispatch; emit APPROVAL_REQUESTED and block if denied.
                # Skip when run_dir is None (in-memory runs / tests) so tests without stakes config can pass.
                # _stakes_trust_band set by _ensure_run_state_initialized; policy loaded once per run above.
                if run_dir is not None and _ws_root_run is not None and _stakes_policy_run is not None:
                    try:
                        from hg_core.stakes import check_gate as stakes_check_gate
                        from hg_core.ledger import emit as ledger_emit
                        _action = _NODE_TYPE_TO_ACTION.get(node.type, "WRITE")
                        _agent_id = (node.assigned_entity or "system").strip() or "system"
                        _budget_used, _trust_band, _escrow_locked = _get_stakes_context(run_state_dict)
                        _gate_result = stakes_check_gate(_action, _agent_id, _budget_used, _trust_band, _escrow_locked, _stakes_policy_run, _ws_root_run)
                        if not _gate_result.allowed:
                            _ev_id = ledger_emit(
                                "APPROVAL_REQUESTED",
                                "node",
                                nid,
                                {"action": _action, "reason": _gate_result.reason, "run_id": run_id, "node_id": nid, "graph_id": dag.graph_id},
                                scope={"type": "run", "id": run_id},
                                workspace_root=_ws_root_run,
                            )
                            node.error = {"code": "GATE_DENIED", "reason": _gate_result.reason, "approval_required": _gate_result.approval_required}
                            node.ended_at = _iso_now()
                            node.status = NodeStatus.FAILED.value
                            self.telemetry("gate_denied", {"run_id": run_id, "node_id": nid, "reason": _gate_result.reason})
                            try:
                                from hg_core.repr_interp.refusal_inspection import is_refusal_inspection_enabled, record_refusal_inspection
                                if is_refusal_inspection_enabled(_ws_root_run, run_state_dict.get("run_config")):
                                    record_refusal_inspection(
                                        _ws_root_run,
                                        _gate_result.reason,
                                        event_id=_ev_id,
                                        run_id=run_id,
                                        node_id=nid,
                                        run_dir=run_dir,
                                        context_ref={"action": _action, "graph_id": dag.graph_id},
                                    )
                            except Exception:
                                logger.warning("Refusal inspection record failed (non-fatal)", exc_info=True)
                            self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                            continue
                    except Exception:
                        logger.warning("Stakes gating/ledger block failed (non-fatal)", exc_info=True)

                # Escrow (Ch1.5): lock before high-impact action (reuse run-scoped policy)
                try:
                    if _stakes_policy_run is not None and _ws_root_run is not None and node.type == "agent":
                        _lock_amt = float((_stakes_policy_run.get("escrow") or {}).get("lock_amount_default", 10.0))
                        from hg_core.ledger import emit as _ledger_emit
                        _ledger_emit(
                            "ESCROW_LOCKED",
                            "node",
                            nid,
                            {"amount": _lock_amt, "action": "dispatch", "run_id": run_id, "graph_id": dag.graph_id},
                            scope={"type": "run", "id": run_id},
                            workspace_root=_ws_root_run,
                        )
                        run_state_dict["_escrow_lock"] = {"node_id": nid, "amount": _lock_amt}
                except Exception:
                    logger.warning("Escrow lock emit failed (non-fatal)", exc_info=True)

                if not node.error:
                    try:
                        output = self._call_dispatcher(dag, node, inputs, run_state, graph_inputs)
                    except Exception as e:
                        output = None
                        classified = classify_failure(e, {"node_id": nid})
                        node.error = {
                            "message": classified["message"],
                            "type": type(e).__name__,
                            "failure_class": classified["failure_class"],
                            "context": classified["context"],
                        }
                    if output is not None and isinstance(output, dict) and not output.get("ok"):
                        raw_err = output.get("error")
                        node.error = raw_err if isinstance(raw_err, dict) else (
                            {"code": "DISPATCH_FAILED", "message": str(raw_err), "type": "DISPATCH_FAILED"}
                            if raw_err else _extract_dispatch_error(output)
                        )
                        if isinstance(node.error, dict) and "failure_class" not in node.error:
                            node.error["failure_class"] = failure_class_from_error_dict(node.error, nid)
                        output = None

                # Budget: after dispatch increment (include tokens/external_calls from dispatcher response)
                observed = {"dispatch_attempts": 1}
                if output is not None and isinstance(output, dict):
                    observed["tokens"] = output.get("tokens", 0) or 0
                    observed["external_calls"] = output.get("external_calls", 0) or 0
                apply_after_dispatch(run_policy_dict, run_state_dict, observed)
                self.telemetry("budget_updated", {"budget_used": dict(run_state_dict.get("budget_used", {}))})

                if rec_token is not None:
                    self.recorder.record_response(
                        rec_token,
                        output if output is not None else {},
                        error=node.error if node.error else None,
                    )

                node.ended_at = _iso_now()
                start_ts = node.started_at
                duration_ms = 0
                if start_ts and node.ended_at:
                    try:
                        t0 = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
                        t1 = datetime.fromisoformat(node.ended_at.replace("Z", "+00:00"))
                        duration_ms = int((t1 - t0).total_seconds() * 1000)
                    except Exception:
                        pass

                if node.error:
                    if node.attempt_count <= node.policy.max_retries:
                        node.status = NodeStatus.READY.value
                        self.telemetry("dag_node_retried", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "attempt_count": node.attempt_count,
                        })
                        time.sleep(node.policy.retry_backoff_ms / 1000.0)
                    else:
                        node.status = NodeStatus.FAILED.value
                        try:
                            _lock = run_state_dict.get("_escrow_lock")
                            if isinstance(_lock, dict) and _lock.get("node_id") == nid and _ws_root_run is not None:
                                from hg_core.ledger import emit as _emit
                                _emit("ESCROW_SLASHED", "node", nid, {"amount": _lock.get("amount", 0), "run_id": run_id}, scope={"type": "run", "id": run_id}, workspace_root=_ws_root_run)
                                run_state_dict["_escrow_lock"] = None
                        except Exception:
                            logger.warning("Escrow slashed emit failed (non-fatal)", exc_info=True)
                        self.telemetry("dag_node_failed", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "status": node.status,
                            "attempt_count": node.attempt_count,
                            "duration_ms": duration_ms,
                            "error_code": node.error.get("type") if isinstance(node.error, dict) else None,
                            **_control_payload(nid, body_to_loop, run_state),
                        })
                        # Steering: after_node (failure path, before fail_fast return or persist)
                        if self.overseer and hasattr(self.overseer, "after_node"):
                            try:
                                self.overseer.after_node(
                                    node,
                                    run_state,
                                    {"ok": False, "error": node.error or {"code": "DISPATCH_FAILED", "message": "unknown"}},
                                )
                            except Exception:
                                pass
                        if failure_mode == "fail_fast":
                            for n in nodes:
                                if n.status == NodeStatus.PENDING.value and any(dep in n.depends_on for dep in [nid]):
                                    n.status = NodeStatus.SKIPPED.value
                            run_state.final_status = "failed"
                            self.state_store.save(run_state, nodes)
                            if run_dir is not None:
                                self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
                            self.telemetry("dag_run_completed", {"graph_id": dag.graph_id, "run_id": run_id, "final_status": "failed"})
                            return self._summary(dag, nodes, run_id, run_state, ok=False)
                        if nid in body_to_loop:
                            loop_id = body_to_loop[nid]
                            loop_node = by_id.get(loop_id)
                            if loop_node and loop_node.type == "loop":
                                on_body_failure = getattr(dag.run_policy, "loop_policy_on_body_failure", "stop_loop")
                                if on_body_failure == "stop_loop":
                                    run_state.loop_state.setdefault(loop_id, {})["active"] = False
                                    body_ids = list((loop_node.inputs or {}).get("body") or [])
                                    for bid in body_ids:
                                        if bid in by_id:
                                            bn = by_id[bid]
                                            if bn.status in (NodeStatus.PENDING.value, NodeStatus.READY.value):
                                                bn.status = NodeStatus.SKIPPED.value
                                                self.telemetry("dag_node_skipped", {
                                                    "graph_id": dag.graph_id,
                                                    "run_id": run_id,
                                                    "node_id": bid,
                                                    "loop_id": loop_id,
                                                    "iteration": ((run_state.loop_state or {}).get(loop_id) or {}).get("iteration"),
                                                    "control_parent": loop_id,
                                                })
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                else:
                    node.status = NodeStatus.DONE.value
                    out = (output.get("outputs") if isinstance(output, dict) and output.get("ok") else output) or {}
                    # Agent nodes: downstream refs (e.g. $node.execute_task.result) expect a "result" key
                    if node.type == "agent" and "result" not in out:
                        out = {"result": out if out else {"status": "completed"}}
                    run_state.node_outputs[nid] = out
                    try:
                        _lock = run_state_dict.get("_escrow_lock")
                        if isinstance(_lock, dict) and _lock.get("node_id") == nid and _ws_root_run is not None:
                            from hg_core.ledger import emit as _emit
                            _emit("ESCROW_RELEASED", "node", nid, {"amount": _lock.get("amount", 0), "run_id": run_id}, scope={"type": "run", "id": run_id}, workspace_root=_ws_root_run)
                            run_state_dict["_escrow_lock"] = None
                    except Exception:
                        logger.warning("Escrow released emit failed (non-fatal)", exc_info=True)
                    _repr_interp_capture_after_node(_ws_root_run, run_id, run_dir, run_state_dict, nid, node.type, dag.graph_id)
                    self.telemetry("dag_node_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "node_id": nid,
                        "status": node.status,
                        "attempt_count": node.attempt_count,
                        "duration_ms": duration_ms,
                        **_control_payload(nid, body_to_loop, run_state),
                    })
                    if node.checkpoints.after and self.overseer:
                        try:
                            self.overseer.checkpoint_after(node, run_state)
                        except Exception:
                            pass
                    # Steering: after_node (success path, after checkpoint_after)
                    if self.overseer and hasattr(self.overseer, "after_node"):
                        try:
                            self.overseer.after_node(
                                node,
                                run_state,
                                output if (output is not None and isinstance(output, dict) and output.get("ok")) else {"ok": True, "outputs": out},
                            )
                        except Exception:
                            pass
                    if self._should_pause(dag, node, "after"):
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        summary = self._summary(dag, nodes, run_id, run_state, ok=True)
                        return {**summary, "status": "paused", "checkpoint": {"node_id": nid, "position": "after"}}
                    self._persist_after_node(run_state, nodes, run_dir, dag, run_id)

        run_state.final_status = compute_final_run_status(nodes, failure_mode)
        self.state_store.save(run_state, nodes)
        if run_dir is not None:
            self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
        self.telemetry("dag_run_completed", {
            "graph_id": dag.graph_id,
            "run_id": run_id,
            "final_status": run_state.final_status,
        })
        ok = run_state.final_status == "completed"
        return self._summary(dag, nodes, run_id, run_state, ok=ok)

    def resume(
        self,
        dag: DAG,
        run_id: str,
        graph_inputs: Optional[Dict[str, Any]] = None,
        run_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Resume a previously persisted run: load state, rebuild nodes, re-enter run loop until no ready and no running."""
        run_dir = Path(run_dir) if run_dir is not None else None  # resume does not support run_dir artifact writing yet
        run_state = self.state_store.load(run_id)
        if not run_state:
            return {"ok": False, "run_id": run_id, "error": "run_not_found"}
        nodes = []
        for n in dag.nodes:
            if n.id in run_state.node_states:
                nodes.append(Node.from_dict(run_state.node_states[n.id]))
            else:
                fresh = Node.from_dict(n.to_dict())
                fresh.status = NodeStatus.PENDING.value
                fresh.attempt_count = 0
                fresh.started_at = None
                fresh.ended_at = None
                fresh.error = None
                nodes.append(fresh)
        graph_inputs = graph_inputs if graph_inputs is not None else dict(dag.inputs)
        _ensure_run_state_initialized(run_state, graph_inputs, run_dir)
        _ws_root_run = _ledger_workspace_root(run_dir) if run_dir else None
        run_id = run_state.run_id
        max_concurrency = dag.run_policy.max_concurrency
        failure_mode = dag.run_policy.failure_mode
        by_id = {n.id: n for n in nodes}
        body_to_loop = _body_to_loop_map(dag)
        # Normalize RUNNING -> READY so resume can make progress (e.g. after crash mid-node).
        for node in nodes:
            if node.status == NodeStatus.RUNNING.value:
                node.status = NodeStatus.READY.value

        while True:
            if _check_steering is not None and run_dir is not None:
                try:
                    action, inject_payload = _check_steering(run_id, run_dir)
                    if action == "inject" and inject_payload is not None:
                        run_state.state["_steering_inject"] = inject_payload
                except Exception as e:  # noqa: BLE001
                    logger.debug("check_steering failed: %s", e)
            cancel_requested, cancel_payload = is_cancel_requested(run_dir)
            if cancel_requested:
                return self._handle_cancel(run_id, dag, nodes, run_state, run_dir, cancel_payload)
            runtime_summary = self._check_runtime_cap(dag, run_id, nodes, run_state, run_dir)
            if runtime_summary is not None:
                return runtime_summary
            ready = get_ready_nodes(dag, nodes, failure_mode)
            if not ready:
                running = [n for n in nodes if n.status == NodeStatus.RUNNING.value]
                if running:
                    break
                if failure_mode == "continue":
                    for n in nodes:
                        if n.status == NodeStatus.PENDING.value and any(
                            by_id.get(dep) and by_id[dep].status == NodeStatus.FAILED.value for dep in n.depends_on
                        ):
                            n.status = NodeStatus.SKIPPED.value
                            self.telemetry("dag_node_skipped", {
                                "graph_id": dag.graph_id,
                                "run_id": run_id,
                                "node_id": n.id,
                            })
                    ready = get_ready_nodes(dag, nodes, failure_mode)
                    if not ready:
                        loop_info = _get_loop_body_complete(dag, nodes, run_state)
                        if loop_info:
                            _advance_loop(dag, nodes, run_state, graph_inputs, loop_info, by_id)
                            continue
                        break
                    continue
                loop_info = _get_loop_body_complete(dag, nodes, run_state)
                if loop_info:
                    _advance_loop(dag, nodes, run_state, graph_inputs, loop_info, by_id)
                    continue
                break

            to_run = ready[:max_concurrency]
            for nid in to_run:
                node = by_id[nid]
                current = node.status or NodeStatus.PENDING.value
                if current == NodeStatus.PENDING.value:
                    node.status = NodeStatus.READY.value
                    current = NodeStatus.READY.value
                if not can_transition(current, NodeStatus.RUNNING.value):
                    continue
                node.status = NodeStatus.RUNNING.value
                node.error = None
                node.started_at = _iso_now()
                node.attempt_count = node.attempt_count + 1
                self.telemetry("dag_node_started", {
                    "graph_id": dag.graph_id,
                    "run_id": run_id,
                    "node_id": nid,
                    "node_type": node.type,
                    "assigned_entity": node.assigned_entity,
                    "attempt_count": node.attempt_count,
                    **_control_payload(nid, body_to_loop, run_state),
                })

                # Gate: evaluate condition, propagate skip (R_skipped - R_taken), mark gate DONE without dispatch
                if node.type == "gate":
                    condition_value = False
                    try:
                        context = {
                            "state": run_state.state,
                            "node": run_state.node_outputs,
                            "graph": {"inputs": graph_inputs},
                            "loop": {},
                        }
                        expression_strict = getattr(dag.run_policy, "expression_strict_mode", False)
                        condition_value = bool(evaluate_expression(
                            (node.inputs or {}).get("condition"),
                            context,
                            strict=expression_strict,
                        ))
                    except Exception:
                        condition_value = False
                    inp = node.inputs or {}
                    true_targets = list(inp.get("true_targets") or [])
                    false_targets = list(inp.get("false_targets") or [])
                    taken = true_targets if condition_value else false_targets
                    non_taken = false_targets if condition_value else true_targets
                    succ = _successors_by_id(nodes)
                    R_taken = _reachable_from(taken, succ) if taken else set()
                    R_skipped = _reachable_from(non_taken, succ) if non_taken else set()
                    to_skip = sorted(R_skipped - R_taken)
                    skipped_ids = {n.id for n in nodes if n.status == NodeStatus.SKIPPED.value}
                    for sid in to_skip:
                        if sid in by_id and by_id[sid].status not in (
                            NodeStatus.DONE.value,
                            NodeStatus.FAILED.value,
                            NodeStatus.SKIPPED.value,
                        ):
                            by_id[sid].status = NodeStatus.SKIPPED.value
                            skipped_ids.add(sid)
                            self.telemetry("dag_node_skipped", {
                                "graph_id": dag.graph_id,
                                "run_id": run_id,
                                "node_id": sid,
                                "gate_id": nid,
                                "gate_taken": condition_value,
                            })
                    _propagate_deps_all_skipped(nodes, skipped_ids)
                    node.status = NodeStatus.DONE.value
                    node.ended_at = _iso_now()
                    run_state.node_outputs[nid] = {"taken": condition_value}
                    self.telemetry("dag_node_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "node_id": nid,
                        "status": node.status,
                        "attempt_count": node.attempt_count,
                        "duration_ms": 0,
                        "gate_taken": condition_value,
                    })
                    if node.checkpoints.after and self.overseer:
                        try:
                            self.overseer.checkpoint_after(node, run_state)
                        except Exception:
                            pass
                    if self._should_pause(dag, node, "after"):
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        summary = self._summary(dag, nodes, run_id, run_state, ok=True)
                        return {**summary, "status": "paused", "checkpoint": {"node_id": nid, "position": "after"}}
                    self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                    continue

                # Loop: evaluate condition once, init loop_state, optionally run first iteration (reset body), mark loop DONE
                if node.type == "loop":
                    body_ids = list((node.inputs or {}).get("body") or [])
                    max_iterations = getattr(node.policy, "max_iterations", None) or 1
                    run_state.state.setdefault("loops", {})[node.id] = run_state.state.get("loops", {}).get(node.id, {})
                    lstate = run_state.loop_state.setdefault(node.id, {})
                    now_ts = datetime.now(timezone.utc).timestamp()
                    lstate["iteration"] = 0
                    lstate["active"] = True
                    lstate["max_iterations"] = max_iterations
                    lstate["iteration_started_at"] = now_ts
                    context = {
                        "state": run_state.state,
                        "node": run_state.node_outputs,
                        "graph": {"inputs": graph_inputs},
                        "loop": {
                            "id": node.id,
                            "iteration": 1,
                            "max_iterations": max_iterations,
                            "state": run_state.state.get("loops", {}).get(node.id, {}),
                        },
                    }
                    expression_strict = getattr(dag.run_policy, "expression_strict_mode", False)
                    condition_value = False
                    try:
                        condition_value = bool(evaluate_expression(
                            (node.inputs or {}).get("condition"),
                            context,
                            strict=expression_strict,
                        ))
                    except Exception:
                        condition_value = False
                    lstate["last_condition_value"] = condition_value
                    if not condition_value:
                        lstate["active"] = False
                        node.status = NodeStatus.DONE.value
                        node.ended_at = _iso_now()
                        run_state.node_outputs[nid] = {}
                        self.telemetry("dag_node_completed", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "status": node.status,
                            "attempt_count": node.attempt_count,
                            "duration_ms": 0,
                        })
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        continue
                    lstate["iteration"] = 1
                    _reset_loop_body_nodes(nodes, by_id, body_ids, run_state)
                    node.status = NodeStatus.DONE.value
                    node.ended_at = _iso_now()
                    run_state.node_outputs[nid] = {"iteration": 1}
                    self.telemetry("dag_node_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "node_id": nid,
                        "status": node.status,
                        "attempt_count": node.attempt_count,
                        "duration_ms": 0,
                        "loop_id": nid,
                        "iteration": 1,
                    })
                    self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                    continue

                # Steering: before_node (before checkpoint_before)
                if self.overseer and hasattr(self.overseer, "before_node"):
                    try:
                        _steering_ret = self.overseer.before_node(node, run_state)
                        if isinstance(_steering_ret, dict) and _steering_ret.get("block"):
                            _reason = _steering_ret.get("reason") or "steering blocked"
                            node.status = NodeStatus.BLOCKED.value
                            node.error = {"code": "STEERING_BLOCKED", "reason": _reason}
                            node.ended_at = _iso_now()
                            if hasattr(self.overseer, "after_node"):
                                try:
                                    self.overseer.after_node(
                                        node,
                                        run_state,
                                        {"ok": False, "error": {"code": "STEERING_BLOCKED", "reason": _reason}},
                                    )
                                except Exception:
                                    pass
                            self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                            continue
                    except Exception:
                        pass

                if node.checkpoints.before and self.overseer:
                    try:
                        self.overseer.checkpoint_before(node, run_state)
                    except Exception:
                        pass

                inputs = resolve_inputs(node, run_state.node_outputs, graph_inputs)
                unresolved = [k for k, v in inputs.items() if isinstance(v, str) and v.startswith("$")]
                input_binding_mode = dag.run_policy.input_binding_mode
                output = None

                if unresolved:
                    if input_binding_mode == "strict":
                        node.error = {"code": "INPUT_RESOLUTION_ERROR", "message": f"Unresolved ref(s): {unresolved}"}
                    elif input_binding_mode == "blocked":
                        node.status = NodeStatus.BLOCKED.value
                        node.error = None
                        node.ended_at = _iso_now()
                        self.telemetry("dag_node_blocked", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "unresolved": unresolved,
                        })
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        continue
                    # lenient: pass through

                run_state.body_to_loop = body_to_loop
                rec_token = None
                if self.recorder and run_dir is not None:
                    ctrl = _control_payload(nid, body_to_loop, run_state)
                    request = build_canonical_request(node, inputs)
                    rec_token = self.recorder.record_request(
                        node_id=nid,
                        attempt_no=node.attempt_count,
                        request=request,
                        loop_id=ctrl.get("loop_id"),
                        iteration=ctrl.get("iteration"),
                    )

                # Budget: before dispatch check (loop-body)
                run_policy_dict = dag.run_policy.to_dict()
                run_state_dict = run_state.state
                cost = {"dispatch_attempts": 1}
                allowed, budget_err = check_before_dispatch(run_policy_dict, run_state_dict, cost)
                if not allowed and budget_err is not None:
                    run_state.final_status = "failed"
                    run_state.updated_at = _iso_now()
                    run_state.state["_run_error"] = budget_err
                    run_state.node_states = {n.id: n.to_dict() for n in nodes}
                    self.state_store.save(run_state, nodes)
                    self.telemetry("budget_exceeded", dict(budget_err))
                    if run_dir is not None:
                        self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
                    self.telemetry("dag_run_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "final_status": run_state.final_status,
                    })
                    return self._summary(dag, nodes, run_id, run_state, ok=False)

                if not node.error:
                    try:
                        output = self._call_dispatcher(dag, node, inputs, run_state, graph_inputs)
                    except Exception as e:
                        output = None
                        classified = classify_failure(e, {"node_id": nid})
                        node.error = {
                            "message": classified["message"],
                            "type": type(e).__name__,
                            "failure_class": classified["failure_class"],
                            "context": classified["context"],
                        }
                    if output is not None and isinstance(output, dict) and not output.get("ok"):
                        raw_err = output.get("error")
                        node.error = raw_err if isinstance(raw_err, dict) else (
                            {"code": "DISPATCH_FAILED", "message": str(raw_err), "type": "DISPATCH_FAILED"}
                            if raw_err else _extract_dispatch_error(output)
                        )
                        if isinstance(node.error, dict) and "failure_class" not in node.error:
                            node.error["failure_class"] = failure_class_from_error_dict(node.error, nid)
                        output = None

                # Budget: after dispatch increment (loop-body; include tokens/external_calls from response)
                observed = {"dispatch_attempts": 1}
                if output is not None and isinstance(output, dict):
                    observed["tokens"] = output.get("tokens", 0) or 0
                    observed["external_calls"] = output.get("external_calls", 0) or 0
                apply_after_dispatch(run_policy_dict, run_state_dict, observed)
                self.telemetry("budget_updated", {"budget_used": dict(run_state_dict.get("budget_used", {}))})

                if rec_token is not None:
                    self.recorder.record_response(
                        rec_token,
                        output if output is not None else {},
                        error=node.error if node.error else None,
                    )

                node.ended_at = _iso_now()
                start_ts = node.started_at
                duration_ms = 0
                if start_ts and node.ended_at:
                    try:
                        t0 = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
                        t1 = datetime.fromisoformat(node.ended_at.replace("Z", "+00:00"))
                        duration_ms = int((t1 - t0).total_seconds() * 1000)
                    except Exception:
                        pass

                if node.error:
                    if node.attempt_count <= node.policy.max_retries:
                        node.status = NodeStatus.READY.value
                        self.telemetry("dag_node_retried", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "attempt_count": node.attempt_count,
                        })
                        time.sleep(node.policy.retry_backoff_ms / 1000.0)
                    else:
                        node.status = NodeStatus.FAILED.value
                        try:
                            _lock = run_state_dict.get("_escrow_lock")
                            if isinstance(_lock, dict) and _lock.get("node_id") == nid and _ws_root_run is not None:
                                from hg_core.ledger import emit as _emit
                                _emit("ESCROW_SLASHED", "node", nid, {"amount": _lock.get("amount", 0), "run_id": run_id}, scope={"type": "run", "id": run_id}, workspace_root=_ws_root_run)
                                run_state_dict["_escrow_lock"] = None
                        except Exception:
                            logger.warning("Escrow slashed emit failed (non-fatal)", exc_info=True)
                        self.telemetry("dag_node_failed", {
                            "graph_id": dag.graph_id,
                            "run_id": run_id,
                            "node_id": nid,
                            "status": node.status,
                            "attempt_count": node.attempt_count,
                            "duration_ms": duration_ms,
                            "error_code": node.error.get("type") if isinstance(node.error, dict) else None,
                            **_control_payload(nid, body_to_loop, run_state),
                        })
                        # Steering: after_node (failure path, before fail_fast return or persist)
                        if self.overseer and hasattr(self.overseer, "after_node"):
                            try:
                                self.overseer.after_node(
                                    node,
                                    run_state,
                                    {"ok": False, "error": node.error or {"code": "DISPATCH_FAILED", "message": "unknown"}},
                                )
                            except Exception:
                                pass
                        if failure_mode == "fail_fast":
                            for n in nodes:
                                if n.status == NodeStatus.PENDING.value and any(dep in n.depends_on for dep in [nid]):
                                    n.status = NodeStatus.SKIPPED.value
                            run_state.final_status = "failed"
                            self.state_store.save(run_state, nodes)
                            if run_dir is not None:
                                self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
                            self.telemetry("dag_run_completed", {"graph_id": dag.graph_id, "run_id": run_id, "final_status": "failed"})
                            return self._summary(dag, nodes, run_id, run_state, ok=False)
                        if nid in body_to_loop:
                            loop_id = body_to_loop[nid]
                            loop_node = by_id.get(loop_id)
                            if loop_node and loop_node.type == "loop":
                                on_body_failure = getattr(dag.run_policy, "loop_policy_on_body_failure", "stop_loop")
                                if on_body_failure == "stop_loop":
                                    run_state.loop_state.setdefault(loop_id, {})["active"] = False
                                    body_ids = list((loop_node.inputs or {}).get("body") or [])
                                    for bid in body_ids:
                                        if bid in by_id:
                                            bn = by_id[bid]
                                            if bn.status in (NodeStatus.PENDING.value, NodeStatus.READY.value):
                                                bn.status = NodeStatus.SKIPPED.value
                                                self.telemetry("dag_node_skipped", {
                                                    "graph_id": dag.graph_id,
                                                    "run_id": run_id,
                                                    "node_id": bid,
                                                    "loop_id": loop_id,
                                                    "iteration": ((run_state.loop_state or {}).get(loop_id) or {}).get("iteration"),
                                                    "control_parent": loop_id,
                                                })
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                else:
                    node.status = NodeStatus.DONE.value
                    out = (output.get("outputs") if isinstance(output, dict) and output.get("ok") else output) or {}
                    # Agent nodes: downstream refs (e.g. $node.execute_task.result) expect a "result" key
                    if node.type == "agent" and "result" not in out:
                        out = {"result": out if out else {"status": "completed"}}
                    run_state.node_outputs[nid] = out
                    try:
                        _lock = run_state_dict.get("_escrow_lock")
                        if isinstance(_lock, dict) and _lock.get("node_id") == nid and _ws_root_run is not None:
                            from hg_core.ledger import emit as _emit
                            _emit("ESCROW_RELEASED", "node", nid, {"amount": _lock.get("amount", 0), "run_id": run_id}, scope={"type": "run", "id": run_id}, workspace_root=_ws_root_run)
                            run_state_dict["_escrow_lock"] = None
                    except Exception:
                        logger.warning("Escrow released emit failed (non-fatal)", exc_info=True)
                    _repr_interp_capture_after_node(_ws_root_run, run_id, run_dir, run_state_dict, nid, node.type, dag.graph_id)
                    self.telemetry("dag_node_completed", {
                        "graph_id": dag.graph_id,
                        "run_id": run_id,
                        "node_id": nid,
                        "status": node.status,
                        "attempt_count": node.attempt_count,
                        "duration_ms": duration_ms,
                        **_control_payload(nid, body_to_loop, run_state),
                    })
                    if node.checkpoints.after and self.overseer:
                        try:
                            self.overseer.checkpoint_after(node, run_state)
                        except Exception:
                            pass
                    # Steering: after_node (success path, after checkpoint_after)
                    if self.overseer and hasattr(self.overseer, "after_node"):
                        try:
                            self.overseer.after_node(
                                node,
                                run_state,
                                output if (output is not None and isinstance(output, dict) and output.get("ok")) else {"ok": True, "outputs": out},
                            )
                        except Exception:
                            pass
                    if self._should_pause(dag, node, "after"):
                        self._persist_after_node(run_state, nodes, run_dir, dag, run_id)
                        summary = self._summary(dag, nodes, run_id, run_state, ok=True)
                        return {**summary, "status": "paused", "checkpoint": {"node_id": nid, "position": "after"}}
                    self._persist_after_node(run_state, nodes, run_dir, dag, run_id)

        run_state.final_status = compute_final_run_status(nodes, failure_mode)
        self.state_store.save(run_state, nodes)
        self.telemetry("dag_run_completed", {
            "graph_id": dag.graph_id,
            "run_id": run_id,
            "final_status": run_state.final_status,
        })
        ok = run_state.final_status == "completed"
        return self._summary(dag, nodes, run_id, run_state, ok=ok)

    def _call_dispatcher(
        self,
        dag: DAG,
        node: Node,
        inputs: Dict[str, Any],
        run_state: RunState,
        graph_inputs: Dict[str, Any],
    ) -> Any:
        """Call dispatcher with optional run_state/graph_inputs/expression_strict for eval nodes."""
        try:
            expression_strict = getattr(dag.run_policy, "expression_strict_mode", False)
            return self.dispatcher(
                node, inputs,
                run_state=run_state,
                graph_inputs=graph_inputs,
                expression_strict=expression_strict,
            )
        except TypeError:
            return self.dispatcher(node, inputs)

    def _summary_dict_for_run_dir(
        self,
        dag: DAG,
        nodes: List[Node],
        run_id: str,
        run_state: RunState,
        run_dir: Path,
    ) -> Dict[str, Any]:
        """Build summary dict for summary.json (run_id, graph_id, started_at, ended_at, final_status, counts, error_summary, run_dir)."""
        done = sum(1 for n in nodes if n.status == NodeStatus.DONE.value)
        failed = sum(1 for n in nodes if n.status == NodeStatus.FAILED.value)
        skipped = sum(1 for n in nodes if n.status == NodeStatus.SKIPPED.value)
        blocked = sum(1 for n in nodes if n.status == NodeStatus.BLOCKED.value)
        error_summary: List[Dict[str, Any]] = []
        for n in nodes:
            if n.status == NodeStatus.FAILED.value and n.error:
                err = n.error
                code = err.get("code", "ERROR") if isinstance(err, dict) else "ERROR"
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                fc = err.get("failure_class") if isinstance(err, dict) else None
                if fc is None and isinstance(err, dict):
                    fc = failure_class_from_error_dict(err, n.id)
                entry = {"node_id": n.id, "code": code, "message": msg, "failure_class": fc or "unknown"}
                error_summary.append(entry)
            if n.status == NodeStatus.BLOCKED.value:
                err = n.error
                msg = (err.get("message", "blocked") if isinstance(err, dict) else str(err)) if err else "blocked"
                fc = "safety_blocked" if isinstance(err, dict) and (err.get("code") == "STEERING_BLOCKED") else "unknown"
                error_summary.append({"node_id": n.id, "code": "BLOCKED", "message": msg, "failure_class": fc})
        run_error = run_state.state.get("_run_error")
        if run_error:
            run_err_dict = run_error if isinstance(run_error, dict) else {}
            fc = run_err_dict.get("failure_class") or failure_class_from_error_dict(run_err_dict, None)
            error_summary.append({
                "node_id": None,
                "code": run_error.get("code", "RUN_ERROR"),
                "message": run_error.get("message", ""),
                "failure_class": fc,
            })
        primary_failure_class = None
        if run_state.final_status == "failed" and error_summary:
            primary_failure_class = error_summary[0].get("failure_class", "unknown")
        out = {
            "run_id": run_id,
            "graph_id": dag.graph_id,
            "started_at": run_state.started_at,
            "ended_at": run_state.updated_at,
            "final_status": run_state.final_status or "completed",
            "counts": {"done": done, "failed": failed, "skipped": skipped, "blocked": blocked},
            "outputs": dict(run_state.node_outputs),
            "error_summary": error_summary,
            "run_dir": str(run_dir),
        }
        if primary_failure_class is not None:
            out["failure_class"] = primary_failure_class
        budget_used = run_state.state.get("budget_used")
        if budget_used is not None:
            out["budget_used"] = dict(budget_used)
        return out

    def _append_run_summary_for_human_notifications(
        self,
        run_dir: Path,
        dag: DAG,
        run_id: str,
        run_state: RunState,
        nodes: List[Node],
    ) -> None:
        """When run is terminal, append to workspace run_summaries.jsonl for overseer ingest."""
        if not run_state.final_status:
            return
        try:
            from hg_core.run_summary_log import append_run_summary
            from hg_core.job_registry import get_operational_session_target, graph_id_to_job_id
        except ImportError:
            return
        try:
            from hg_lib.config import get_workspace_root
            workspace_root = get_workspace_root()
        except Exception:
            workspace_root = run_dir.parent.parent.parent
        display_job_id = graph_id_to_job_id(dag.graph_id) or dag.graph_id
        session_target = get_operational_session_target(display_job_id) or f"automation-{display_job_id}"
        node_outputs = run_state.node_outputs or {}
        notify_out = node_outputs.get("prepare_notification")
        if isinstance(notify_out, dict):
            outputs = notify_out.get("outputs") or {}
            payload = outputs.get("notification_payload") if isinstance(outputs, dict) else None
        else:
            payload = None
        if isinstance(payload, dict):
            try:
                from . import native_task_tools as _nt
                entry = {"timestamp": run_state.updated_at or "", "task_name": display_job_id, "channel": "human", "summary": payload.get("summary") or {}}
                summary_text = _nt._format_lifecycle_notification(entry)
            except Exception:
                entry = {"timestamp": run_state.updated_at or "", "task_name": display_job_id, "channel": "human", "summary": {"execution": {"status": run_state.final_status or "unknown"}}}
                summary_text = _nt._format_lifecycle_notification(entry)
        else:
            # Never write raw DAG run message; always lifecycle format so ingest sends the correct human notification.
            try:
                from . import native_task_tools as _nt
                entry = {"timestamp": run_state.updated_at or "", "task_name": display_job_id, "channel": "human", "summary": {"execution": {"status": run_state.final_status or "unknown"}}}
                summary_text = _nt._format_lifecycle_notification(entry)
            except Exception:
                status = run_state.final_status or "unknown"
                run_ts = run_state.updated_at or ""
                summary_text = (
                    f"*Lifecycle run complete*\n"
                    f"- task: `{display_job_id}`\n"
                    f"- status: `{status}`\n"
                    f"- timestamp: `{run_ts}`"
                )
        append_run_summary(
            workspace_root,
            job_id=display_job_id,
            session_target=session_target,
            summary=summary_text,
            status=run_state.final_status or "ok",
            run_id=run_id,
        )

    def _should_pause(self, dag: DAG, node: Node, position: str) -> bool:
        """True if run should pause at this checkpoint (HITL). position is 'before' or 'after'."""
        run_policy = dag.run_policy
        pause_at = getattr(run_policy, "pause_at_checkpoint", False)
        cps = node.checkpoints
        if position == "before":
            if getattr(cps, "pause_before", False):
                return True
            return bool(pause_at and cps.before)
        if position == "after":
            if getattr(cps, "pause_after", False):
                return True
            return bool(pause_at and cps.after)
        return False

    def _persist_after_node(
        self,
        run_state: RunState,
        nodes: List[Node],
        run_dir: Optional[Path],
        dag: DAG,
        run_id: str,
        node_id: Optional[str] = None,
        reason: str = "persist",
    ) -> None:
        """Persist state after a node terminal transition (durable workflow). Optionally write state_history snapshot."""
        run_state.node_states = {n.id: n.to_dict() for n in nodes}
        self.state_store.save(run_state, nodes)
        if run_dir is not None:
            self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
            state_history_write_snapshot(
                run_dir, run_state.to_dict(), reason=reason, node_id=node_id
            )

    def _write_run_dir_artifacts(
        self,
        run_dir: Path,
        dag: DAG,
        nodes: List[Node],
        run_id: str,
        run_state: RunState,
    ) -> None:
        """Write state.json and summary.json to run_dir. If behavior_events.jsonl exists, build and persist delegation graph and summary."""
        run_state.node_states = {n.id: n.to_dict() for n in nodes}
        (run_dir / "state.json").write_text(
            json.dumps(run_state.to_dict(), indent=2), encoding="utf-8"
        )
        summary = self._summary_dict_for_run_dir(dag, nodes, run_id, run_state, run_dir)
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        if run_state.final_status:
            self._append_run_summary_for_human_notifications(run_dir, dag, run_id, run_state, nodes)
        behavior_path = run_dir / "behavior_events.jsonl"
        if behavior_path.exists():
            try:
                from . import delegation_graph as _dg
                from . import delegation_quality as _dq
                from . import intervention_policy as _ip
                events = []
                with open(behavior_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        events.append(json.loads(line))
                final_status = run_state.final_status or "success"
                graph_dict, summary_dict = _dg.build_graph_from_events(
                    run_id, dag.graph_id, events, root_objective_summary=dag.inputs.get("goal", "")
                )
                summary_dict["final_state"]["status"] = final_status
                metrics = summary_dict.get("metrics", {})
                from . import emergent_behavior_detectors as _ebd
                node_attempts = {n.id: getattr(n, "attempt_count", 0) for n in nodes}
                anomalies = _ebd.run_default_detectors(
                    metrics, events=events, node_attempts=node_attempts
                )
                summary_dict["anomalies"] = anomalies
                quality_result = _dq.check_quality(
                    metrics, nodes=graph_dict.get("nodes"), edges=graph_dict.get("edges")
                )
                intervention = _ip.current_intervention(
                    {**metrics, "anomalies": summary_dict.get("anomalies", [])}
                )
                summary_dict["quality"] = quality_result
                summary_dict["intervention"] = intervention
                blocked = _ip.should_block_external_writes(
                    intervention["step"], quality_result["degraded"]
                )
                summary_dict["final_state"]["external_writes_attempted"] = "no"
                summary_dict["final_state"]["external_writes_blocked"] = "yes" if blocked else "no"
                _dg.persist_delegation_artifacts(run_dir, graph_dict, summary_dict)
            except Exception:
                pass

    def _handle_cancel(
        self,
        run_id: str,
        dag: DAG,
        nodes: List[Node],
        run_state: RunState,
        run_dir: Optional[Path],
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mark run as cancelled, persist state, emit telemetry, and return summary."""
        reason = ""
        if isinstance(payload, dict):
            reason = str(payload.get("reason") or payload.get("message") or "")
        run_state.final_status = "cancelled"
        run_state.updated_at = _iso_now()
        run_state.state["_run_error"] = {
            "code": "RUN_CANCELLED",
            "message": reason or "cancel requested",
        }
        run_state.node_states = {n.id: n.to_dict() for n in nodes}
        self.state_store.save(run_state, nodes)
        if run_dir is not None:
            self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
        self.telemetry("dag_run_cancelled", {
            "graph_id": dag.graph_id,
            "run_id": run_id,
            "reason": reason or "cancel requested",
        })
        self.telemetry("dag_run_completed", {
            "graph_id": dag.graph_id,
            "run_id": run_id,
            "final_status": run_state.final_status,
        })
        return self._summary(dag, nodes, run_id, run_state, ok=False)

    def _check_runtime_cap(
        self,
        dag: DAG,
        run_id: str,
        nodes: List[Node],
        run_state: RunState,
        run_dir: Optional[Path],
    ) -> Optional[Dict[str, Any]]:
        """Fail the run when run_policy.max_total_runtime_s is exceeded."""
        max_total_runtime_s = getattr(dag.run_policy, "max_total_runtime_s", None)
        if max_total_runtime_s is None:
            return None
        started_epoch = _as_epoch(run_state.started_at)
        if started_epoch <= 0:
            return None
        elapsed_s = max(0.0, time.time() - started_epoch)
        if elapsed_s <= float(max_total_runtime_s):
            return None

        run_state.final_status = "failed"
        run_state.updated_at = _iso_now()
        run_state.state["_run_error"] = {
            "code": "MAX_TOTAL_RUNTIME_EXCEEDED",
            "message": (
                f"max_total_runtime_s cap ({max_total_runtime_s}) exceeded after "
                f"{elapsed_s:.3f}s"
            ),
        }
        run_state.node_states = {n.id: n.to_dict() for n in nodes}
        self.state_store.save(run_state, nodes)
        if run_dir is not None:
            self._write_run_dir_artifacts(run_dir, dag, nodes, run_id, run_state)
        self.telemetry("dag_run_completed", {
            "graph_id": dag.graph_id,
            "run_id": run_id,
            "final_status": run_state.final_status,
        })
        return self._summary(dag, nodes, run_id, run_state, ok=False)

    def _summary(
        self,
        dag: DAG,
        nodes: List[Node],
        run_id: str,
        run_state: RunState,
        ok: bool,
    ) -> Dict[str, Any]:
        run_state.node_states = {n.id: n.to_dict() for n in nodes}
        return {
            "ok": ok,
            "run_id": run_id,
            "graph_id": dag.graph_id,
            "status": run_state.final_status,
            "final_status": run_state.final_status,
            "nodes": {n.id: {"status": n.status, "attempt_count": n.attempt_count, "error": n.error} for n in nodes},
            "node_outputs": dict(run_state.node_outputs),
            "run_state": run_state.to_dict(),
        }
