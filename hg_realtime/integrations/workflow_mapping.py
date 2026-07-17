"""Resolve event (event_type, payload) to (workflow_id, resolved_inputs). Single source: DAG_JOB_REGISTRY + workflow_registry."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..schemas.event import Event, EventType

_SOCIAL_TIMER_MODES = {"auto-post", "engage"}


def _get_job_registry() -> Tuple[Any, Any]:
    """Load DAG_JOB_REGISTRY and get_runtime_job from scripts/dag_runtime_jobs. Returns (registry_dict, get_runtime_job) or (None, None)."""
    try:
        from hg_lib.config import get_workspace_root
        root = get_workspace_root()
    except Exception:
        root = None
    if not root:
        return None, None
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return None, None
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from dag_runtime_jobs import DAG_JOB_REGISTRY, get_runtime_job  # type: ignore[import-untyped]
        return DAG_JOB_REGISTRY, get_runtime_job
    except Exception:
        return None, None


def _canonical_task_name(job_or_task_id: str) -> str:
    text = str(job_or_task_id or "").strip()
    if not text:
        return ""
    try:
        from hg_core.job_registry import task_name_for_job_id

        return task_name_for_job_id(text) or text
    except Exception:
        return text


def _resolve_social_timer_workflow(job_or_task_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    canonical_task = _canonical_task_name(job_or_task_id)
    if not canonical_task:
        return None
    try:
        from hg_core.job_registry import get_mode, get_platform
    except Exception:
        return None

    platform = str(get_platform(canonical_task) or "").strip().lower()
    mode = str(get_mode(canonical_task) or "").strip().lower()
    if not platform or mode not in _SOCIAL_TIMER_MODES:
        return None
    return "social-media", {
        "task_name": canonical_task,
        "preferred_task_name": canonical_task,
        "platform": platform,
        "mode": mode,
        "platforms": [platform],
        "scheduler_model": "single_entity_directed_cadence",
        "requested_job_id": str(job_or_task_id or "").strip(),
        "trigger": "realtime",
    }


def route_event_to_workflow(e: Event) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Map event to (workflow_id, resolved_inputs). TIMER: payload workflow_id or job_id;
    job_id is resolved via DAG_JOB_REGISTRY (task_name/DAG path). UI_ACTION run_workflow same.
    """
    if e.event_type == EventType.TIMER:
        payload = e.payload or {}
        # Swarm: payload.swarm_tasks is list of {workflow_id, inputs} or {tool_name, args} → route as "swarm"
        if isinstance(payload.get("swarm_tasks"), list):
            return "swarm", dict(payload)
        # Phase 7: batch_ingest → analyze-files (file.parse per path) or web-search (search per url/query)
        batch = payload.get("batch_ingest")
        if isinstance(batch, dict):
            wf = (batch.get("workflow_id") or batch.get("workflow")) or ""
            files = batch.get("files") or []
            urls = batch.get("urls") or []
            queries = batch.get("queries") or []
            tasks: list = []
            if wf in ("analyze-files", "analyze_files") and files:
                tasks = [{"tool_name": "file.parse", "args": {"path": str(p)}} for p in files[:50]]
            elif wf in ("web-search", "web_search") and (urls or queries):
                tasks = [{"tool_name": "search.fetch_url", "args": {"url": str(u)}} for u in urls[:100]]
                tasks += [{"tool_name": "search.query", "args": {"q": str(q)}} for q in queries[:100]]
                tasks = tasks[:100]
            if tasks:
                return "swarm", {
                    "swarm_tasks": tasks,
                    "max_children": len(tasks),
                    "summary": batch.get("summary", f"batch {wf}"),
                    **{k: v for k, v in payload.items() if k not in ("batch_ingest",)},
                }

        workflow_id = payload.get("workflow_id")
        job_id = payload.get("job_id")
        inputs = dict(payload.get("inputs") or {})

        if workflow_id:
            if job_id:
                inputs.setdefault("scheduler_job_id", str(job_id))
                inputs.setdefault("requested_job_id", str(job_id))
            return str(workflow_id), inputs
        if job_id:
            social_route = _resolve_social_timer_workflow(str(job_id))
            if social_route is not None:
                workflow_name, social_inputs = social_route
                social_inputs.update(inputs)
                social_inputs.setdefault("requested_job_id", str(job_id))
                social_inputs.setdefault("trigger", "realtime")
                return workflow_name, social_inputs
            _registry, get_job = _get_job_registry()
            if get_job:
                job = get_job(str(job_id))
                if job:
                    # Use job inputs as base (e.g. ("trigger=cron", "goal=..."))
                    base: Dict[str, Any] = {}
                    job_inputs = getattr(job, "inputs", None)
                    if isinstance(job_inputs, (list, tuple)):
                        for item in job_inputs:
                            if isinstance(item, str) and "=" in item:
                                k, _, v = item.partition("=")
                                base[k.strip()] = v.strip()
                            elif isinstance(item, str):
                                base[f"arg_{len(base)}"] = item
                    base.update(inputs)
                    return str(job_id), base
            return str(job_id), inputs

    if e.event_type == EventType.UI_ACTION and (e.payload or {}).get("action") == "run_workflow":
        payload = e.payload or {}
        return str(payload.get("workflow_id", "")), dict(payload.get("inputs") or {})

    return None
