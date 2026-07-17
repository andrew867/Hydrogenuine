"""Swarm controller: build plan, spawn children (lease + launch), wait for completions, reduce, write artifacts."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .contracts import MAX_SWARM_CHILDREN, SwarmPlan, SwarmResult
from .quantum_nodes import reduce_for_plan, swarm_spawn_quantum

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..integrations.dag_launcher import DagLauncher
    from ..integrations.run_index import RunIndexReader
    from ..scheduler.models import RunRequested


def _get_job_id(workflow_id: str) -> Optional[str]:
    """Resolve job_id from workflow_id via DAG_JOB_REGISTRY."""
    try:
        from hg_lib.config import get_workspace_root
        root = get_workspace_root()
    except Exception:
        root = None
    if not root:
        return None
    import sys
    scripts_dir = root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from dag_runtime_jobs import get_runtime_job  # type: ignore[import-untyped]
        job = get_runtime_job(workflow_id)
        return getattr(job, "job_id", workflow_id) if job else workflow_id
    except Exception:
        return workflow_id


def _run_dir(workspace: Path, workflow_id: str, run_id: str) -> Path:
    """Path to a child run's directory (summary.json lives here)."""
    job_id = _get_job_id(workflow_id) or workflow_id
    return workspace / "memory" / "automation" / "dag_runs" / job_id / run_id


def _load_summary(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load summary.json from run_dir if present."""
    path = run_dir / "summary.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


class SwarmController:
    """
    Runs a SwarmPlan: launch children (capped by max_children, max 100), wait for completions,
    reduce outputs, write SwarmResult to artifacts.
    """

    def __init__(
        self,
        *,
        launcher: "DagLauncher",
        run_index_reader: Optional["RunIndexReader"] = None,
        workspace: Optional[Path] = None,
        max_children_cap: int = MAX_SWARM_CHILDREN,
        poll_interval_s: float = 1.0,
    ) -> None:
        self._launcher = launcher
        self._run_index = run_index_reader
        self._workspace = workspace or _workspace_root()
        self._max_cap = min(max_children_cap, MAX_SWARM_CHILDREN)
        self._poll_interval_s = poll_interval_s

    def run(self, plan: SwarmPlan) -> SwarmResult:
        """Spawn up to max_children children (DAG jobs or L10 tool tasks), wait for DAG completions, reduce, write artifacts."""
        from ..scheduler.models import RunRequested

        swarm_run_id = str(uuid.uuid4())
        correlation_id = plan.correlation_id or swarm_run_id
        cap = min(plan.max_children, self._max_cap)
        to_launch = plan.tasks[:cap]

        spawn_payloads: Optional[List[Dict[str, Any]]] = None
        quantum_meta: Dict[str, Any] = {}
        try:
            from hg_quantum.config import is_enabled

            use_quantum_spawn = (
                is_enabled("symmetry_breaking")
                or is_enabled("state_correlation")
                or getattr(plan, "force_quantum", False)
            )
            if use_quantum_spawn:
                spawn_payloads, quantum_meta = swarm_spawn_quantum(
                    plan=plan,
                    correlation_id=correlation_id,
                )
        except Exception as exc:
            logger.warning("swarm_spawn_quantum hook failed; continuing classic spawn: %s", exc)

        # Each entry: (run_id or "", workflow_id or "", sync_result or None). sync_result set for tool tasks.
        run_ids: List[str] = []
        workflow_ids: List[str] = []
        sync_results: List[Optional[Dict[str, Any]]] = []  # for tool tasks, result; for DAG, None

        for i, t in enumerate(to_launch):
            if t.get("tool_name"):
                # Phase 7: direct L10 tool invocation (e.g. file.parse, search.fetch_url)
                ok, out = self._invoke_tool_task(plan, t)
                run_ids.append("")
                workflow_ids.append("")
                sync_results.append(out if out else {"ok": ok, "status": "failed"})
                continue
            # DAG child
            inputs = dict(t.get("inputs") or {})
            if spawn_payloads and i < len(spawn_payloads):
                payload = spawn_payloads[i]
                if payload.get("inputs"):
                    inputs = {**payload.get("inputs", {}), **inputs}
                if payload.get("quantum"):
                    inputs["quantum"] = payload["quantum"]
            if "run_config" not in inputs:
                inputs["run_config"] = {}
            rc = inputs["run_config"]
            if not isinstance(rc, dict):
                rc = {}
            if plan.max_wall_clock_s_per_child and "timeout_s" not in rc:
                rc["timeout_s"] = plan.max_wall_clock_s_per_child
            inputs["run_config"] = rc
            rr = RunRequested(
                request_id=str(uuid.uuid4()),
                workflow_id=str(t.get("workflow_id", "")),
                tenant_id=plan.tenant_id,
                actor_id=plan.actor_id,
                correlation_id=plan.correlation_id or swarm_run_id,
                resolved_inputs=inputs,
            )
            run_id = self._launcher.launch(rr)
            run_ids.append(run_id)
            workflow_ids.append(rr.workflow_id)
            sync_results.append(None)

        deadline = None
        if plan.max_wall_clock_s is not None and plan.max_wall_clock_s > 0:
            deadline = time.monotonic() + plan.max_wall_clock_s

        child_outputs: List[Dict[str, Any]] = []
        child_statuses: List[str] = []
        for i, (run_id, wf_id, sync_out) in enumerate(zip(run_ids, workflow_ids, sync_results)):
            if sync_out is not None:
                child_outputs.append(sync_out)
                child_statuses.append("completed" if sync_out.get("ok") else "failed")
            else:
                ok, summary = self._wait_for_run(run_id, wf_id, deadline)
                child_statuses.append("completed" if ok else "failed")
                child_outputs.append(summary if summary else {"run_id": run_id, "status": "failed"})

        completed = sum(1 for s in child_statuses if s == "completed")
        failed = len(child_statuses) - completed
        if failed == 0:
            status = "completed"
        elif completed == 0:
            status = "failed"
        else:
            status = "partial"

        summary_str, artifacts_dict, warnings_list = reduce_for_plan(
            plan=plan,
            child_outputs=child_outputs,
            swarm_run_id=swarm_run_id,
        )
        counts = {"launched": len([r for r in run_ids if r]), "completed": completed, "failed": failed}

        result = SwarmResult(
            swarm_run_id=swarm_run_id,
            correlation_id=plan.correlation_id or swarm_run_id,
            child_run_ids=list(run_ids),
            child_outputs=child_outputs,
            child_statuses=child_statuses,
            status=status,
            counts=counts,
            summary=summary_str,
            artifacts={**artifacts_dict, "counts": counts, "child_run_ids": run_ids, "quantum_spawn": quantum_meta},
            warnings=warnings_list,
            artifacts_path=None,
        )

        # Write SwarmResult to artifacts
        artifacts_dir = self._workspace / "memory" / "automation" / "swarm_runs"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifacts_dir / f"{swarm_run_id}.json"
        payload = {
            "swarm_run_id": result.swarm_run_id,
            "correlation_id": result.correlation_id,
            "child_run_ids": result.child_run_ids,
            "child_statuses": result.child_statuses,
            "status": result.status,
            "counts": result.counts,
            "summary": result.summary,
            "artifacts": result.artifacts,
            "warnings": result.warnings,
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        result.artifacts_path = str(artifact_path)

        return result

    def _invoke_tool_task(self, plan: SwarmPlan, task: Dict[str, Any]) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Invoke L10 tool (file.parse, search.query, search.fetch_url); return (ok, result dict)."""
        from ..integrations.tool_router import ToolCall, execute
        from ..integrations.tool_registry import build_default_registry
        from ..integrations.idempotency_store import InMemoryIdempotencyStore

        tool_name = str(task.get("tool_name", ""))
        args = dict(task.get("args") or task.get("inputs") or {})
        if not tool_name:
            return False, {"ok": False, "error": "tool_name required"}
        # Idempotency key from path or url or query
        path = args.get("path") or args.get("url") or args.get("q") or args.get("query") or ""
        if tool_name == "file.parse" and path:
            from ..integrations.file_tools import idempotency_key_for_file_parse
            key = idempotency_key_for_file_parse(str(path))
        else:
            import hashlib
            key = "swarm-" + hashlib.sha256(f"{tool_name}:{path}".encode()).hexdigest()[:24]
        if tool_name == "file.parse" and "workspace" not in args:
            args = {**args, "workspace": str(self._workspace)}
        call = ToolCall(
            tool_name=tool_name,
            args=args,
            idempotency_key=key,
            correlation_id=plan.correlation_id or "swarm",
            run_id="swarm",
        )
        store = InMemoryIdempotencyStore()
        reg = build_default_registry()
        try:
            raw = execute(call, reg, store)
        except Exception as e:
            return False, {"ok": False, "error": str(e)}
        ok = bool(raw.get("ok"))
        return ok, raw

    def _wait_for_run(
        self,
        run_id: str,
        workflow_id: str,
        deadline: Optional[float],
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Poll until run completes or deadline. Returns (ok, summary_dict)."""
        run_dir = _run_dir(self._workspace, workflow_id, run_id)
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                return False, {"run_id": run_id, "status": "timeout"}

            if self._run_index:
                rec = self._run_index.get_run(run_id)
                if rec and rec.status in ("completed", "failed"):
                    summary = None
                    if rec.run_dir:
                        summary = _load_summary(Path(rec.run_dir))
                    if not summary:
                        summary = {"run_id": run_id, "status": rec.status}
                    return rec.status == "completed", summary

            summary = _load_summary(run_dir)
            if summary is not None:
                ok = summary.get("final_status") == "completed" or summary.get("ok") is True
                return ok, summary

            time.sleep(self._poll_interval_s)


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return Path.cwd()
