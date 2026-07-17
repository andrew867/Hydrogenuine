"""Wire console run/resume to hg_core TaskGraphExecutor."""

from pathlib import Path
import json
import sys
from typing import Any, Dict, Optional

from ..core.config import settings

# Ensure workspace root is on path so hg_core is importable when running from operator_console/server
_workspace_root = Path(__file__).resolve().parents[4]
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from hg_core.task_graph import DAG, TaskGraphExecutor
from hg_core.task_graph.state_store import StateStore
from hg_core.task_graph.tool_contract_setup import build_default_tool_contract
from hg_core.task_graph.tool_adapter_contract import ToolAdapter, ToolError, ToolResult
from hg_core.task_graph.native_task_tools import run_task_tool
from hg_core.wrappers.decision_context import record_decision


def _tool_effect(registry: Any, tool_name: str) -> str:
    try:
        desc = registry.get(tool_name)
        effect = getattr(desc, "effect_class", "none")
        return effect if isinstance(effect, str) else "none"
    except Exception:
        return "none"


def _record_approval(tool_name: str, inputs: Dict[str, Any], *, idempotency_key: Optional[str], effect: str) -> None:
    if effect != "write":
        return
    goal = str(inputs.get("goal") or "").strip()
    rationale = f"WorkerToolAdapter approved write invocation for {tool_name}"
    if goal:
        rationale = f"{rationale} with goal: {goal[:180]}"
    alternatives = ["deny and require manual replay", "route as read-only draft mode"]
    context_bits = []
    if idempotency_key:
        context_bits.append(f"idempotency_key={idempotency_key}")
    context_bits.append(f"effect_class={effect}")
    context = ", ".join(context_bits)
    record_decision(
        agent_id=tool_name,
        action=f"worker_tool_invoke:{tool_name}",
        rationale=rationale,
        alternatives=alternatives,
        context=context,
        outcome="approved",
    )


class WorkerToolAdapter(ToolAdapter):
    """Operator-console adapter that invokes task tools and records write approvals."""

    def __init__(self, *, registry: Optional[Any] = None) -> None:
        self.registry = registry

    def invoke(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> ToolResult:
        effect = _tool_effect(self.registry, tool_name)
        _record_approval(tool_name, inputs, idempotency_key=idempotency_key, effect=effect)

        tool_result = run_task_tool(tool_name, inputs, timeout_s=timeout_s or 300)
        if tool_result is None:
            return ToolResult(
                ok=False,
                outputs={},
                error=ToolError(
                    code="TOOL_NOT_AVAILABLE",
                    message="No execution path registered for this tool",
                ),
            )

        ok = bool(tool_result.get("ok"))
        outputs = tool_result.get("outputs") if isinstance(tool_result.get("outputs"), dict) else {}
        error_payload = tool_result.get("error")
        error_code = tool_result.get("error_code") or "TOOL_ERROR"
        if isinstance(error_payload, dict) and error_payload.get("code"):
            error_code = error_payload.get("code")
        if not ok and not error_payload:
            error_payload = tool_result.get("stderr") or tool_result.get("error")

        usage: Optional[Dict[str, Any]] = None
        if "external_calls" in tool_result or "tokens" in tool_result:
            usage = {}
            for key in ("external_calls", "tokens", "bytes_in", "bytes_out"):
                if key in tool_result:
                    usage[key] = tool_result[key]
            if not usage:
                usage = None

        metadata: Optional[Dict[str, Any]] = None
        if tool_result.get("returncode") is not None:
            metadata = {"returncode": tool_result.get("returncode"), "effect_class": effect}

        error = None
        if not ok:
            error = ToolError(code=str(error_code), message=str(error_payload or "tool invocation failed"))

        return ToolResult(ok=ok, outputs=outputs or {}, error=error, usage=usage, metadata=metadata)


def _run_dir(run_id: str) -> Path:
    root = Path(settings.runs_root)
    root.mkdir(parents=True, exist_ok=True)
    rd = root / run_id
    rd.mkdir(parents=True, exist_ok=True)
    return rd


def _tool_contract() -> tuple:
    registry, _ = build_default_tool_contract()
    return registry, WorkerToolAdapter(registry=registry)


def run_inprocess(run_id: str, dag: dict) -> dict:
    """Run DAG in-process via TaskGraphExecutor; write artifacts to run_dir."""
    rd = _run_dir(run_id)
    state_store = StateStore(base_dir=Path(settings.runs_root))
    registry, adapter = _tool_contract()
    executor = TaskGraphExecutor(state_store=state_store, tool_registry=registry, tool_adapter=adapter)
    dag_obj = DAG.from_dict(dag)
    graph_inputs = dict(dag.get("inputs") or {})
    result = executor.run(dag_obj, run_id=run_id, run_dir=rd, graph_inputs=graph_inputs)
    if result.get("ok") is False:
        return {
            "run_id": run_id,
            "graph_id": dag.get("graph_id"),
            "status": result.get("final_status") or "failed",
            "started_at": None,
            "ended_at": None,
            "run_dir": str(rd),
        }
    run_state = result.get("run_state", {})
    return {
        "run_id": run_id,
        "graph_id": result.get("graph_id", dag.get("graph_id")),
        "status": result.get("status") or result.get("final_status", "completed"),
        "started_at": run_state.get("started_at"),
        "ended_at": run_state.get("updated_at"),
        "run_dir": str(rd),
    }


def resume_inprocess(run_id: str, run_dir: str) -> dict:
    """Resume a run: load DAG from run_dir, call executor.resume."""
    rd = Path(run_dir)
    graph_path = rd / "graph.reviewed.json" if (rd / "graph.reviewed.json").exists() else rd / "graph.json"
    if not graph_path.exists():
        return {"run_id": run_id, "status": "failed", "error": "graph not found"}
    dag_dict = json.loads(graph_path.read_text(encoding="utf-8"))
    dag_obj = DAG.from_dict(dag_dict)
    state_store = StateStore(base_dir=Path(settings.runs_root))
    registry, adapter = _tool_contract()
    executor = TaskGraphExecutor(state_store=state_store, tool_registry=registry, tool_adapter=adapter)
    result = executor.resume(dag_obj, run_id, run_dir=rd)
    if result.get("ok") is False:
        return {"run_id": run_id, "status": result.get("status") or "failed"}
    run_state = result.get("run_state", {})
    return {
        "run_id": run_id,
        "status": result.get("status") or run_state.get("final_status", "completed"),
    }
