"""
Dispatch layer: map node.type + assigned_entity to execution handlers.

For agent nodes, invokes existing run_task (subprocess) so DAG runs use
the same context and memory policy as standalone agent runs.
For eval nodes, evaluates expression and optional writes to run_state.state (atomic, on success only).
For transform and gate nodes, uses built-in deterministic handlers.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .schema import Node
from .expression import evaluate as evaluate_expression


def _set_state_by_dot_path(state: Dict[str, Any], path: str, value: Any) -> None:
    """Set state at dot path, creating nested dicts. path is relative to state (e.g. 'loops.L.counter')."""
    if not path or ".." in path:
        raise ValueError(f"Invalid state write path: {path!r}")
    parts = [p.strip() for p in path.split(".") if p.strip()]
    if not parts:
        raise ValueError(f"Invalid state write path: {path!r}")
    cur: Any = state
    for i, key in enumerate(parts[:-1]):
        if not isinstance(cur, dict):
            raise ValueError(f"Write path {path!r}: segment {key!r} is not a dict")
        if key not in cur:
            cur[key] = {}
        cur = cur[key]
    if not isinstance(cur, dict):
        raise ValueError(f"Write path {path!r}: parent of {parts[-1]!r} is not a dict")
    cur[parts[-1]] = value


def _parse_stdout_for_thread_result(stdout: str) -> Optional[Dict[str, Any]]:
    """
    Parse agent stdout for a JSON object containing thread_id or thread_url (e.g. from fourclaw posting script).
    Returns dict with thread_id and thread_url (building URL from thread_id if needed), or None.
    """
    if not stdout or not isinstance(stdout, str):
        return None
    # Try last lines first (script often prints JSON at end)
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if "thread_id" not in line and "thread_url" not in line:
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue
            thread_id = obj.get("thread_id")
            thread_url = obj.get("thread_url")
            if thread_id and not thread_url:
                thread_url = f"https://www.4claw.org/t/{thread_id}"
            if thread_id or thread_url:
                return {"thread_id": thread_id, "thread_url": thread_url}
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def dispatch_agent(
    task_name: str,
    resolved_inputs: Dict[str, Any],
    memory_profile: Any = None,
    timeout_s: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run an agent task by invoking hg_core.run_task in a subprocess.

    For fourclaw-auto-post when resolved_inputs contains a goal, uses the DAG direct-post path
    (goal -> title/content -> fourclaw_auto_post_async) so a real post is created and
    thread_id/thread_url are returned in outputs. See dag_wiring_plan.md.
    """
    timeout = timeout_s if timeout_s is not None and timeout_s > 0 else 300

    # Prefer native task-tool execution when a task has a first-class runtime
    # handler. This keeps scheduled DAG jobs on the same explicit execution path
    # as tool nodes for approvals, monitor/maintenance jobs, and research jobs.
    try:
        from .native_task_tools import run_task_tool

        native_out = run_task_tool(task_name, resolved_inputs, timeout_s=timeout)
        if native_out is not None:
            return native_out
    except Exception:
        pass

    use_agent_env = os.environ.get("HG_DAG_POST_USE_AGENT", "").strip().lower() in ("1", "true", "yes")
    session_runner_set = (
        os.environ.get("HG_DAG_USE_SESSION_RUNNER", "").strip().lower() in ("1", "true", "yes")
        and (os.environ.get("HG_SESSION_RUNNER_CMD", "").strip() or "")
    )

    # When USE_AGENT=1 and session runner configured: run full 4claw agent via session runner (skip direct-post).
    # If runner fails because the executable is not found (e.g. WinError 2 on Windows with "hg"),
    # fall back to direct-post so we still get a post and thread_url.
    if task_name == "fourclaw-auto-post" and resolved_inputs.get("goal") and use_agent_env and session_runner_set:
        try:
            from .session_runner import run_via_session_runner
            session_out = run_via_session_runner(task_name, resolved_inputs, memory_profile=memory_profile, timeout_s=timeout)
            if session_out and session_out.get("ok"):
                return session_out
            err = (session_out or {}).get("error") or ""
            err_str = err.lower() if isinstance(err, str) else ""
            if isinstance(err, str) and (
                "WinError 2" in err or "cannot find the file" in err_str or "cannot find the file specified" in err_str
            ):
                pass  # fall through to direct-post so we still get a post URL
            elif session_out:
                return session_out
        except Exception as e:
            err = str(e)
            if "WinError 2" in err or "cannot find the file" in err.lower():
                pass  # fall through to direct-post
            else:
                return {"ok": False, "error": str(e), "returncode": -1}

    # DAG direct-post path: fourclaw-auto-post with goal creates post in-process (persona+memory when USE_LLM=1)
    if task_name == "fourclaw-auto-post" and resolved_inputs.get("goal"):
        try:
            from .fourclaw_dag_post import run_fourclaw_post_from_goal
            goal = resolved_inputs.get("goal")
            if isinstance(goal, dict):
                goal = goal.get("value", goal.get("text", str(goal)))
            goal_str = str(goal or "").strip()
            if goal_str:
                out = run_fourclaw_post_from_goal(
                    goal=goal_str,
                    board=resolved_inputs.get("board") or "b",
                    timeout_s=timeout,
                )
                if out.get("ok") and out.get("outputs"):
                    return out
                return {"ok": out.get("ok", False), "error": out.get("error", "unknown"), "returncode": out.get("returncode", 1)}
        except Exception as e:
            return {"ok": False, "error": str(e), "returncode": -1}

    # Session-runner path: when configured, run agent via external runner (section 4 of dag_wiring_plan.md)
    try:
        from .session_runner import run_via_session_runner
        session_out = run_via_session_runner(task_name, resolved_inputs, memory_profile=memory_profile, timeout_s=timeout)
        if session_out:
            return session_out
    except Exception:
        pass

    try:
        cmd = [
            sys.executable,
            "-m",
            "hg_core.run_task",
            task_name,
        ]
        env = dict(os.environ)
        env["HG_DAG_INPUTS"] = json.dumps(resolved_inputs)
        env["HG_MEMORY_PROFILE"] = (memory_profile or "") if isinstance(memory_profile, str) else ""
        inputs_path = None
        try:
            fd, inputs_path = tempfile.mkstemp(suffix=".json", prefix="hg_dag_inputs_")
            os.close(fd)
            with open(inputs_path, "w", encoding="utf-8") as f:
                json.dump(resolved_inputs, f)
            cmd.extend(["--inputs", inputs_path])
        except Exception:
            pass
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        finally:
            if inputs_path and os.path.exists(inputs_path):
                try:
                    os.unlink(inputs_path)
                except Exception:
                    pass
        ok = result.returncode == 0
        stdout_str = (result.stdout or "") if result.stdout else ""
        stdout_tail = stdout_str[-2000:]  # keep more for parsing
        out: Dict[str, Any] = {
            "ok": ok,
            "returncode": result.returncode,
            "stdout_tail": stdout_tail[-500:] if len(stdout_tail) > 500 else stdout_tail,
        }
        # If agent stdout contains thread_id/thread_url (e.g. fourclaw post), expose as outputs for node_outputs
        thread_result = _parse_stdout_for_thread_result(stdout_str)
        if thread_result:
            out["outputs"] = {"result": thread_result}
        else:
            # Downstream refs (e.g. $node.execute_task.result) require a "result" key
            out["outputs"] = {"result": {"status": "completed" if ok else "failed", "returncode": result.returncode}}
        return out
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "returncode": -1}
    except Exception as e:
        return {"ok": False, "error": str(e), "returncode": -1}


def dispatch_node(
    node: Node,
    resolved_inputs: Dict[str, Any],
    run_state: Optional[Any] = None,
    graph_inputs: Optional[Dict[str, Any]] = None,
    expression_strict: bool = False,
) -> Dict[str, Any]:
    """
    Dispatch a single node based on node.type and assigned_entity.

    - agent: run_task(assigned_entity)
    - eval: evaluate expression, apply writes to run_state.state (atomic, on success only), return outputs
    - tool: native task tool dispatch (or empty outputs)
    - transform: deterministic transform of resolved inputs to outputs
    - gate: evaluate condition and return gate decision outputs
    """
    if node.type == "agent":
        memory_profile = getattr(node.policy, "memory_profile", None)
        timeout_s = getattr(node.policy, "timeout_s", None)
        return dispatch_agent(node.assigned_entity, resolved_inputs, memory_profile, timeout_s=timeout_s)

    if node.type == "eval":
        return _dispatch_eval(node, resolved_inputs, run_state, graph_inputs, expression_strict)

    if node.type == "tool":
        try:
            from .native_task_tools import run_task_tool

            tool_out = run_task_tool(
                node.assigned_entity,
                resolved_inputs,
                timeout_s=getattr(node.policy, "timeout_s", None) or 300,
                memory_profile=getattr(node.policy, "memory_profile", None),
            )
            if tool_out is not None:
                return tool_out
        except Exception as e:
            return {"ok": False, "error": str(e), "returncode": -1}
        return {"ok": True, "outputs": {}}

    if node.type == "transform":
        return _dispatch_transform(node, resolved_inputs, run_state, graph_inputs, expression_strict)

    if node.type == "gate":
        return _dispatch_gate(node, resolved_inputs, run_state, graph_inputs, expression_strict)

    return {"ok": False, "error": {"code": "UNSUPPORTED_NODE_TYPE", "message": f"Unsupported node type: {node.type}"}}


def _in_loop_body(run_state: Optional[Any]) -> bool:
    """True if run_state has an active loop iteration."""
    if not run_state or not getattr(run_state, "loop_state", None):
        return False
    for s in (run_state.loop_state or {}).values():
        if (s or {}).get("active"):
            return True
    return False


def _dispatch_tool_with_contract(
    node: Node,
    resolved_inputs: Dict[str, Any],
    run_state: Optional[Any],
    registry: Any,
    tool_adapter: Any,
    expression_strict: bool = False,
    rate_limiter: Optional[Any] = None,
    on_rate_exceed: str = "raise",
) -> Dict[str, Any]:
    """Dispatch a tool node via registry and adapter with validate_tool_call / validate_tool_result."""
    from .tool_registry import ToolRegistry
    from .tool_adapter_contract import ToolAdapter
    from .tool_validator import validate_tool_call, validate_tool_result

    tool_name = node.assigned_entity
    desc = registry.get(tool_name)
    if rate_limiter is not None and desc.rate_limit:
        rate_limiter.check(tool_name, desc.rate_limit, on_exceed=on_rate_exceed)
    retries = getattr(node.policy, "max_retries", 0) or 0
    in_loop = _in_loop_body(run_state)
    idempotency_key = getattr(node.policy, "idempotency_key", None)
    if idempotency_key is not None and not isinstance(idempotency_key, str):
        idempotency_key = str(idempotency_key)

    validated = validate_tool_call(
        registry,
        tool_name,
        resolved_inputs,
        idempotency_key=idempotency_key,
        retries=retries,
        in_loop_body=in_loop,
    )
    timeout_s = validated.get("timeout_s")
    if timeout_s is None:
        timeout_s = getattr(node.policy, "timeout_s", None)
    # desc already resolved above for rate_limiter
    result = tool_adapter.invoke(
        tool_name,
        resolved_inputs,
        idempotency_key=idempotency_key,
        timeout_s=timeout_s,
    )
    validate_tool_result(desc, result, strict=expression_strict)

    out: Dict[str, Any] = {
        "ok": result.ok,
        "outputs": result.outputs or {},
    }
    if result.error:
        out["error"] = result.error.message
        out["error_code"] = getattr(result.error, "code", "unknown")
    if result.usage:
        out["usage"] = result.usage
    if result.metadata:
        out["metadata"] = result.metadata
    return out


def make_tool_contract_dispatcher(
    registry: Any,
    tool_adapter: Any,
    base_dispatcher: Optional[Any] = None,
    rate_limiter: Optional[Any] = None,
    on_rate_exceed: str = "raise",
) -> Any:
    """
    Return a dispatcher that uses the tool contract for tool nodes and delegates otherwise.
    Use as executor's dispatcher when tool_registry and tool_adapter are configured.
    If rate_limiter is provided, per-tool rate limits are enforced before invoke.
    """
    base = base_dispatcher or dispatch_node

    def dispatcher(
        node: Node,
        resolved_inputs: Dict[str, Any],
        run_state: Optional[Any] = None,
        graph_inputs: Optional[Dict[str, Any]] = None,
        expression_strict: bool = False,
    ) -> Dict[str, Any]:
        if node.type == "tool" and registry is not None and tool_adapter is not None:
            return _dispatch_tool_with_contract(
                node,
                resolved_inputs,
                run_state,
                registry,
                tool_adapter,
                expression_strict,
                rate_limiter=rate_limiter,
                on_rate_exceed=on_rate_exceed,
            )
        return base(node, resolved_inputs, run_state=run_state, graph_inputs=graph_inputs, expression_strict=expression_strict)

    return dispatcher


def _dispatch_eval(
    node: Node,
    resolved_inputs: Dict[str, Any],
    run_state: Optional[Any],
    graph_inputs: Optional[Dict[str, Any]],
    expression_strict: bool,
) -> Dict[str, Any]:
    """
    Eval node: evaluate inputs.expression; optionally apply inputs.writes to state (atomic, only on success).
    Writes apply only on success; invalid write path in lenient fails the eval and no writes are applied.
    """
    context = _build_expression_context(run_state, graph_inputs)

    expr = (node.inputs or {}).get("expression")
    if expr is None:
        return {"ok": False, "error": {"code": "EVAL_ERROR", "message": "eval node requires inputs.expression"}}

    try:
        result = evaluate_expression(expr, context, strict=expression_strict)
    except ValueError as e:
        return {"ok": False, "error": {"code": "EVAL_ERROR", "message": str(e), "type": "ValueError"}}

    writes = (node.inputs or {}).get("writes")
    if writes and isinstance(writes, dict) and run_state is not None and hasattr(run_state, "state"):
        # Evaluate all write values first (no mutations yet)
        apply_list: list = []
        for path, value_expr in writes.items():
            if not isinstance(path, str) or not path.startswith("state."):
                return {
                    "ok": False,
                    "error": {"code": "WRITE_PATH_ERROR", "message": f"Write path must start with 'state.': {path!r}"},
                }
            try:
                val = evaluate_expression(value_expr, context, strict=expression_strict)
                apply_list.append((path, val))
            except ValueError as e:
                return {"ok": False, "error": {"code": "EVAL_ERROR", "message": str(e), "type": "ValueError"}}
        # Apply all writes atomically: apply to a copy, then replace state (so no partial apply on failure)
        state_copy = copy.deepcopy(run_state.state)
        try:
            for path, val in apply_list:
                _set_state_by_dot_path(state_copy, path[6:].strip("."), val)
        except ValueError as e:
            return {"ok": False, "error": {"code": "WRITE_PATH_ERROR", "message": str(e), "type": "ValueError"}}
        run_state.state.clear()
        run_state.state.update(state_copy)

    out_key = next(iter(node.outputs.keys()), "result") if isinstance(node.outputs, dict) and node.outputs else "result"
    outputs = {out_key: result}
    return {"ok": True, "outputs": outputs}


def _build_expression_context(run_state: Optional[Any], graph_inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build expression context shared by eval/transform/gate nodes."""
    state = (run_state.state if run_state else {}) if hasattr(run_state or {}, "state") else {}
    node_outputs = (run_state.node_outputs if run_state else {}) if hasattr(run_state or {}, "node_outputs") else {}
    graph_inputs = graph_inputs or {}
    loop_ctx: Dict[str, Any] = {}
    if run_state and hasattr(run_state, "loop_state"):
        for loop_id, lstate in (run_state.loop_state or {}).items():
            if lstate.get("active"):
                loop_ctx = {
                    "id": loop_id,
                    "iteration": lstate.get("iteration"),
                    "max_iterations": lstate.get("max_iterations"),
                    "state": (state or {}).get("loops", {}).get(loop_id, {}),
                }
                break
    return {
        "state": state,
        "node": node_outputs,
        "graph": {"inputs": graph_inputs},
        "loop": loop_ctx,
    }


def _dispatch_transform(
    node: Node,
    resolved_inputs: Dict[str, Any],
    run_state: Optional[Any],
    graph_inputs: Optional[Dict[str, Any]],
    expression_strict: bool,
) -> Dict[str, Any]:
    """Transform node: expression transform (when provided) or structural pass-through."""
    context = _build_expression_context(run_state, graph_inputs)
    transformed: Any
    if "expression" in resolved_inputs:
        try:
            transformed = evaluate_expression(resolved_inputs.get("expression"), context, strict=expression_strict)
        except ValueError as e:
            return {"ok": False, "error": {"code": "TRANSFORM_ERROR", "message": str(e), "type": "ValueError"}}
    elif len(resolved_inputs) == 1:
        transformed = next(iter(resolved_inputs.values()))
    else:
        transformed = dict(resolved_inputs)

    outputs: Dict[str, Any] = {"result": transformed}
    declared = list(node.outputs.keys()) if isinstance(node.outputs, dict) else []
    if declared:
        if isinstance(transformed, dict):
            for key in declared:
                outputs[key] = transformed.get(key, transformed if len(declared) == 1 else None)
        else:
            outputs[declared[0]] = transformed
    return {"ok": True, "outputs": outputs}


def _dispatch_gate(
    node: Node,
    resolved_inputs: Dict[str, Any],
    run_state: Optional[Any],
    graph_inputs: Optional[Dict[str, Any]],
    expression_strict: bool,
) -> Dict[str, Any]:
    """Gate node: evaluate condition and return selected branch targets."""
    context = _build_expression_context(run_state, graph_inputs)
    condition = resolved_inputs.get("condition")
    if condition is None:
        condition = resolved_inputs.get("allow", True)

    if isinstance(condition, bool):
        allowed = condition
    else:
        try:
            allowed = bool(evaluate_expression(condition, context, strict=expression_strict))
        except ValueError as e:
            return {"ok": False, "error": {"code": "GATE_CONDITION_ERROR", "message": str(e), "type": "ValueError"}}

    true_targets = resolved_inputs.get("true_targets")
    false_targets = resolved_inputs.get("false_targets")
    selected_targets = []
    if isinstance(true_targets, list) and isinstance(false_targets, list):
        selected_targets = true_targets if allowed else false_targets

    return {
        "ok": True,
        "outputs": {
            "allowed": allowed,
            "condition_value": allowed,
            "selected_targets": selected_targets,
        },
    }
