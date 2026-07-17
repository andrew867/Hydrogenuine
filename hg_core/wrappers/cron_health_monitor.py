#!/usr/bin/env python3
"""
Cron Workflow Health Monitor

Checks if any cron jobs are overdue or failing. Uses hg_lib.config.
Output: JSON with status, alerts, and recommendations.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from hg_core.job_registry import task_name_for_job_id
from hg_core.temporal_changelog import record_major_disruption_once
from hg_lib.config import get_cron_jobs_path, get_workspace_root
from hg_lib.errors import structured_error_result
from hg_lib.platform_utils import ensure_utf8_stdio

ERROR_PATTERNS = [
    r"(?i)an\s+(unexpected|unknown|unhandled)\s+error\s+occurred",
    r"(?i)error:\s*an\s+(unexpected|unknown)",
    r"(?i)traceback\s*\(most\s+recent\s+call\s+last\)",
    r"(?i)exception\s+(raised|occurred|thrown)",
    r"(?i)failed\s+with\s+exit\s+code",
    r"(?i)script\s+execution\s+failed",
    r"(?i)command\s+exited\s+with\s+code\s+[1-9]",
    r"(?i)subprocess\s+(failed|error)",
    r"(?i)calledprocesserror",
    r"(?i)file\s+not\s+found\s+error",
    r"(?i)permission\s+denied",
    r"(?i)import\s+error",
    r"(?i)module\s+not\s+found",
    r"(?i)syntax\s+error",
    r"(?i)indentation\s+error",
    r"(?i)valueerror",
    r"(?i)typeerror",
    r"(?i)keyerror",
    r"(?i)attributeerror",
    r"(?i)ioerror",
    r"(?i)oserror",
    r"(?i)connection\s+error",
    r"(?i)timeout\s+(error|expired)",
    r"(?i)http\s+error\s+\d{3}",
    r"(?i)status\s+code\s+[45]\d{2}",
    r"(?i)spawn\s+enametoolong",
    r"(?i)enametoolong",
    r"(?i)enoent.*no\s+such\s+file\s+or\s+directory",
    r"(?i)exec.*failed.*spawn",
    r"(?i)⚠️.*exec.*failed",
    r"(?i)⚠️.*read\s+failed",
    r"(?i)⚠️.*error",
]

# Minimum lastRunAtMs to consider "has run" (avoid ancient/zero treated as overdue).
MIN_VALID_LAST_RUN_MS = 86400000  # 1 day after epoch

# Overdue threshold (ms) per job_id for schedule.kind == "every". If missing, use everyMs * default_multiplier.
# Keys are canonical task_name (use task_name_for_job_id(job_id) when looking up by job_id)
EXPECTED_INTERVALS = {
    "every": {
        "moltbook-auto-post": 1860001 * 2,
        "moltbook-engage": 1020000 * 2,
        "fourclaw-auto-post": 1200000 * 2,
        "fourclaw-engage": 660000 * 2,
        "knowledge-research-auto": 3600000 * 2,
        "overseer-monitor": 300000 * 2,
        "aichan-auto-post": 900000 * 2,
        "aichan-engage": 1800000 * 2,
        "agentchan-auto-post": 1500000 * 2,
        "agentchan-engage": 900000 * 2,
        "memory-maintenance": 3600000 * 2,  # 1h * 2
    },
    "default_multiplier": 2,
}

CRITICAL_JOBS = {
    "memory-maintenance",
    "overseer-monitor",
    "moltbook-auto-post",
    "moltbook-engage",
    "fourclaw-auto-post",
    "fourclaw-engage",
    "aichan-auto-post",
    "aichan-engage",
    "agentchan-auto-post",
    "agentchan-engage",
}


def detect_error_patterns(text: str) -> list:
    """Detect error patterns in text output."""
    if not text:
        return []
    return [
        p for p in ERROR_PATTERNS
        if re.search(p, text, re.IGNORECASE)
    ]


def check_job_health(job: dict, now_ms: int) -> dict:
    """Check if a job is healthy (not overdue, not failing)."""
    job_id = job.get("id", "unknown")
    enabled = job.get("enabled", False)
    if not enabled:
        return {
            "healthy": True,
            "status": "disabled",
            "message": f"{job_id} is disabled",
        }
    state = job.get("state", {})
    last_run_ms = state.get("lastRunAtMs")
    last_status = state.get("lastStatus")
    last_error = (state.get("lastError") or "").strip()
    schedule = job.get("schedule", {})
    schedule_kind = schedule.get("kind")
    # Treat 0, None, or invalid (e.g. ancient) as never run — do not compute overdue
    if last_run_ms is None or last_run_ms == 0 or (isinstance(last_run_ms, (int, float)) and last_run_ms < MIN_VALID_LAST_RUN_MS):
        return {
            "healthy": False,
            "status": "never_run",
            "message": f"{job_id} has never run",
        }
    # Delivery-only failure: task completed but downstream human notification failed — treat as healthy.
    if last_status == "error" and last_error and "cron announce delivery failed" in last_error.lower():
        return {
            "healthy": True,
            "status": "delivery_failed",
            "message": f"{job_id} completed; notification delivery failed (not counted as failing)",
        }
    if last_status and last_status != "ok":
        return {
            "healthy": False,
            "status": "failing",
            "message": f"{job_id} last run failed with status: {last_status}",
        }
    if schedule_kind == "every":
        every_ms = schedule.get("everyMs", 0)
        canonical = task_name_for_job_id(job_id) or job_id
        threshold_ms = EXPECTED_INTERVALS["every"].get(
            canonical,
            every_ms * EXPECTED_INTERVALS["default_multiplier"],
        )
    elif schedule_kind == "cron":
        threshold_ms = 24 * 60 * 60 * 1000
    else:
        return {
            "healthy": True,
            "status": "unknown",
            "message": f"{job_id} has unknown schedule type: {schedule_kind}",
        }
    time_since_last_run_ms = now_ms - last_run_ms
    if time_since_last_run_ms > threshold_ms:
        return {
            "healthy": False,
            "status": "overdue",
            "message": (
                f"{job_id} is overdue by "
                f"{(time_since_last_run_ms - threshold_ms) / 1000 / 60:.1f} minutes"
            ),
            "overdue_by_ms": time_since_last_run_ms - threshold_ms,
        }
    return {
        "healthy": True,
        "status": "ok",
        "message": f"{job_id} is healthy",
    }


def maybe_record_cron_disruption(summary: dict, workspace_root: Path) -> None:
    results = summary.get("results") if isinstance(summary.get("results"), list) else []
    unhealthy = [row for row in results if not row.get("healthy") and row.get("enabled", False)]
    if not unhealthy:
        return
    critical = [
        row for row in unhealthy
        if str(row.get("job_id") or "") in CRITICAL_JOBS
        or str(task_name_for_job_id(str(row.get("job_id") or "")) or "") in CRITICAL_JOBS
    ]
    major = [
        row for row in unhealthy
        if row.get("status") == "failing"
        or float(row.get("overdue_by_ms") or 0) >= 6 * 60 * 60 * 1000
    ]
    impacted = critical or major
    if not impacted:
        return
    names = [str(row.get("workflow_label") or row.get("job_id") or "job") for row in impacted[:3]]
    summary_text = "Scheduled work was delayed or unavailable."
    if names:
        summary_text += f" Affected: {', '.join(names)}."
    record_major_disruption_once(
        title="Scheduler disruption",
        summary=summary_text,
        workspace_root=workspace_root,
        dedupe_key="cron_health:major_disruption",
        kind="outage",
        severity="high",
        tags=["scheduler", "outage"],
        affected_entities=["all"],
        details={"jobs": names, "unhealthy_count": len(unhealthy)},
        within_hours=12,
    )


def main() -> None:
    """Main entry point."""
    ensure_utf8_stdio()
    try:
        jobs_file = get_cron_jobs_path()
        if not jobs_file.exists():
            raise FileNotFoundError(
                f"Could not find jobs.json at {jobs_file}"
            )
        with open(jobs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        jobs = data.get("jobs", [])
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        results = []
        unhealthy_count = 0
        alerts = []
        for job in jobs:
            health = check_job_health(job, now_ms)
            results.append({
                "job_id": job.get("id"),
                "workflow_label": job.get("name"),
                "enabled": job.get("enabled", False),
                **health,
            })
            if not health["healthy"] and job.get("enabled", False):
                unhealthy_count += 1
                alerts.append(health["message"])
        all_healthy = unhealthy_count == 0
        summary = {
            "ok": all_healthy,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "total_jobs": len([j for j in jobs if j.get("enabled", False)]),
            "healthy_jobs": len([
                r for r in results
                if r["healthy"] and r.get("enabled", False)
            ]),
            "unhealthy_jobs": unhealthy_count,
            "alerts": alerts if alerts else ["All jobs healthy"],
            "results": results,
            "recommendations": [],
        }
        workspace = get_workspace_root()
        logs_dir = workspace / "memory" / "cron-logs"
        hidden_errors = []
        if logs_dir.exists():
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            log_file = logs_dir / f"{today}.jsonl"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            workflow_label = entry.get("workflow_label") or entry.get("job_name") or "unknown"
                            status = entry.get("status", "unknown")
                            output_preview = entry.get(
                                "output_preview", ""
                            )
                            error_field = entry.get("error", "")
                            combined = f"{output_preview} {error_field}".strip()
                            if combined and status == "ok":
                                patterns = detect_error_patterns(combined)
                                if patterns:
                                    hidden_errors.append({
                                        "workflow_label": workflow_label,
                                        "timestamp": entry.get(
                                            "timestamp", ""
                                        ),
                                        "patterns_found": len(patterns),
                                    })
                        except json.JSONDecodeError:
                            pass
        if hidden_errors:
            all_healthy = False
            for h in hidden_errors:
                alerts.append(
                    f"{h['workflow_label']}: Error patterns in output (status was 'ok')"
                )
            summary["hidden_errors"] = hidden_errors
            summary["recommendations"].append(
                f"Found {len(hidden_errors)} job(s) with error patterns in output."
            )
        if not all_healthy:
            summary["recommendations"].append(
                "Check cron job logs and job configuration."
            )
        maybe_record_cron_disruption(summary, workspace)
        print(json.dumps(summary, indent=2))
        sys.exit(0 if all_healthy else 1)
    except FileNotFoundError as e:
        out = structured_error_result(
            e, code="JOBS_FILE_NOT_FOUND", context={"recommendations": ["Ensure Hydrogenuine is installed and cron is configured"]}
        )
        print(json.dumps(out, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        out = structured_error_result(
            e, code="CRON_HEALTH_ERROR", context={"recommendations": ["Check if jobs.json is valid JSON", "Verify file permissions"]}
        )
        print(json.dumps(out, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
