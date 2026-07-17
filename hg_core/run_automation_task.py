#!/usr/bin/env python3
"""
Run an automation task as a tool.

This script can either:
1. Force-start a cron job (if job_id is provided)
2. Execute the task directly by reading the task file

Usage:
    python -m hg_core.run_automation_task --task <task-name> [--force-cron] [--job-id <job-id>]
"""
import sys
import json
import argparse

from hg_lib.config import get_task_file_path, resolve_task_file_name
from hg_lib.platform_utils import ensure_utf8_stdio

from hg_core.job_registry import get_model, get_session_target


def find_cron_job_id(task_name: str) -> str:
    """Map task name to realtime schedule job_id. All automation tasks use the realtime runner and memory/automation/realtime_schedule.json."""
    task_to_job = {
        # Engage (realtime_schedule.json)
        "moltbook-engage": "social-media",
        "fourclaw-engage": "social-media",
        "aichan-engage": "social-media",
        "agentchan-engage": "social-media",
        "moltx-engage": "social-media",
        # Auto-post (realtime_schedule.json)
        "moltbook-auto-post": "social-media",
        "fourclaw-auto-post": "social-media",
        "aichan-auto-post": "social-media",
        "agentchan-auto-post": "social-media",
        "social-media": "social-media",
        # Other scheduled
        "overseer-monitor": "overseer-monitor",
        "memory-maintenance": "memory-maintenance",
        "knowledge-research-auto-v2": "knowledge-research-auto-v2",
        "moltstack-draft": "moltstack-draft",
        "moltstack-publish": "moltstack-publish",
        "rcmp-job-search": "rcmp-job-search-monitor",
        # Legacy / alternate cron (if used)
        "polymarket-summary": "polymarket-morning-summary",
        "memory-manager": "memory-manager-2h-check",
    }
    return task_to_job.get(task_name)


def force_start_cron_job(job_id: str) -> dict:
    """Force start a cron job by triggering it via Hydrogenuine API or direct execution."""
    from pathlib import Path

    cron_dir = Path.home() / ".hg" / "cron"
    jobs_file = cron_dir / "jobs.json"

    if not jobs_file.exists():
        return {"ok": False, "error": "Cron jobs file not found"}

    try:
        with open(jobs_file, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)

        job = next(
            (j for j in jobs_data.get("jobs", []) if j.get("id") == job_id), None
        )
        if not job:
            return {"ok": False, "error": f"Job {job_id} not found"}

        return {
            "ok": True,
            "action": "cron_job_triggered",
            "job_id": job_id,
            "workflow_label": job.get("name"),
            "message": (
                f"Cron job {job_id} would be triggered. "
                "Use --direct to execute task directly."
            ),
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to read cron jobs: {str(e)}"}


def execute_task_directly(task_name: str) -> dict:
    """Return native-runtime execution guidance for a task.
    Session target is resolved from job_registry (single source of truth)."""
    task_file = get_task_file_path(task_name)

    if not task_file.exists():
        return {"ok": False, "error": f"Task file not found: {task_file}"}

    # Resolve session_target from job_registry so aliases (e.g. aichan-post -> automation-aichan-auto-post) work
    session_target = get_session_target(task_name) or f"automation-{task_name}"
    task_file_path = f"skills/automation/tasks/{resolve_task_file_name(task_name)}.md"
    try:
        from operator_console.server.app.services.operational_agency_control import build_agency_control_summary
        from hg_lib.config import get_workspace_root
        from hg_core.job_registry import get_operational_agent_id, get_operational_session_target

        agency_control_summary = build_agency_control_summary(
            root=get_workspace_root(),
            binding={
                "operational_agent_id": get_operational_agent_id(task_name),
                "operational_session_target": get_operational_session_target(task_name),
            },
            session_target=session_target,
        )
    except Exception:
        agency_control_summary = {
            "status": "unavailable",
            "mode": "normal",
            "effective_mode": "normal",
        }

    result = {
        "ok": True,
        "action": "native_runtime_execution",
        "task_name": task_name,
        "task_file": task_file_path,
        "session_target": session_target,
        "execution_mode": "native_runtime_contract",
        "agency_control_summary": agency_control_summary,
        "instruction_request_tool": "lifecycle.get_runtime_contract",
        "notify_tool": "lifecycle.notify_human",
        "sleep_tool": "lifecycle.request_sleep",
        "message": (
            f"Use the native runtime contract for {task_name}. "
            f"Keep the isolated session target {session_target} so continuity and receipts stay coherent."
        ),
        "instructions": (
            f"Execute automation task: {task_name}\n\n"
            "Request compact execution guidance through lifecycle.get_runtime_contract. "
            f"Run inside the existing isolated session ({session_target}). "
            "Use native runtime tools for work, human notification, and bounded sleep instead of relying on task-file choreography."
        ),
    }
    effective_mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    if effective_mode == "held":
        result["message"] = (
            f"{task_name} is currently held by persona-local agency control. "
            f"Leave a blocked receipt instead of performing outbound work."
        )
        result["instructions"] += (
            f"\n\nAgency control is held. Do not perform the task. "
            f"Reason: {agency_control_summary.get('reason') or 'operator hold'}."
        )
    elif effective_mode == "review_only":
        result["message"] = (
            f"{task_name} is currently in review-only mode. "
            f"Do not perform autonomous outbound work without operator review."
        )
        result["instructions"] += (
            f"\n\nAgency control is review-only. "
            f"Prefer receipts, drafts, and review-safe work. "
            f"Reason: {agency_control_summary.get('reason') or 'operator review required'}."
        )
    model = get_model(task_name)
    if model:
        result["model"] = model
    return result


def main():
    try:
        ensure_utf8_stdio()
    except ImportError:
        pass

    ap = argparse.ArgumentParser(description="Run automation task as tool")
    ap.add_argument("--task", required=True, help="Task name (e.g., moltbook-auto-post)")
    ap.add_argument(
        "--force_cron", action="store_true", help="Force start cron job instead of direct execution"
    )
    ap.add_argument(
        "--job_id", help="Specific cron job ID (auto-detected if not provided)"
    )

    args = ap.parse_args()

    if args.force_cron:
        job_id = args.job_id or find_cron_job_id(args.task)
        if not job_id:
            result = {"ok": False, "error": f"No cron job found for task: {args.task}"}
        else:
            result = force_start_cron_job(job_id)
    else:
        result = execute_task_directly(args.task)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
