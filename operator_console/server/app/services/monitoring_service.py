"""Aggregated monitoring insight for DAG runtime operational visibility."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from .run_index_db import list_runs as list_index_runs
from hg_lib.config import get_workspace_root

DAG_RUNTIME_COMMAND = "python scripts/run_dag_job.py --job-id "
DAG_JOB_TO_DAG_PATH = {
    "social-media": "memory/automation/dags/social_media.json",
    "fourclaw-auto-post-cadence": "memory/automation/dags/fourclaw_auto_post.json",
    "fourclaw-engage": "memory/automation/dags/fourclaw_engage.json",
    "moltbook-auto-post": "memory/automation/dags/moltbook_auto_post.json",
    "moltbook-engage": "memory/automation/dags/moltbook_engage.json",
    "aichan-auto-post": "memory/automation/dags/aichan_auto_post.json",
    "aichan-engage": "memory/automation/dags/aichan_engage.json",
    "agentchan-auto-post": "memory/automation/dags/agentchan_auto_post.json",
    "agentchan-engage": "memory/automation/dags/agentchan_engage.json",
    "rcmp-job-search-monitor": "memory/automation/dags/job_search_degree_agnostic_agent_runtime_v1.json",
    "knowledge-research-auto": "memory/automation/dags/knowledge_research_auto.json",
    "knowledge-research-auto-v2": "memory/automation/dags/knowledge_research_auto_v2.json",
    "overseer-monitor": "memory/automation/dags/overseer_monitor.json",
    "moltstack-draft": "memory/automation/dags/moltstack_draft.json",
    "moltstack-publish": "memory/automation/dags/moltstack_publish.json",
    "memory-maintenance": "memory/automation/dags/memory_maintenance.json",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, PermissionError, json.JSONDecodeError):
        return None


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    d0 = xs[f] * (c - k)
    d1 = xs[c] * (k - f)
    return d0 + d1


def _is_failed(status: str | None, final_status: str | None) -> bool:
    s = (status or "").lower()
    fs = (final_status or "").lower()
    return s in {"failed", "error"} or fs in {"failed", "error"}


def _extract_duration_s(run: dict[str, Any]) -> float | None:
    started = run.get("started_at")
    ended = run.get("ended_at")
    if isinstance(started, (int, float)) and isinstance(ended, (int, float)) and ended >= started:
        return float(ended - started)
    return None


def _extract_policy_violations(summary: dict[str, Any] | None) -> int:
    if not summary:
        return 0
    out = 0
    for e in summary.get("error_summary") or []:
        if not isinstance(e, dict):
            continue
        fc = (e.get("failure_class") or "").lower()
        code = (e.get("code") or "").upper()
        if fc == "safety_blocked" or code in {"STEERING_BLOCKED", "BLOCKED"}:
            out += 1
    return out


def _extract_blocked_nodes(summary: dict[str, Any] | None) -> int:
    if not summary:
        return 0
    counts = summary.get("counts") or {}
    blocked = counts.get("blocked", 0)
    return blocked if isinstance(blocked, int) and blocked >= 0 else 0


def _load_dag_runtime_config() -> dict[str, Any]:
    jobs_path = Path.home() / ".hg" / "cron" / "jobs.json"
    configured_jobs: list[str] = []
    configured_dag_paths: list[str] = []
    configured_workflows: set[str] = set()
    try:
        if jobs_path.exists():
            payload = json.loads(jobs_path.read_text(encoding="utf-8"))
            for job in payload.get("jobs", []):
                if not isinstance(job, dict):
                    continue
                jid = job.get("id")
                msg = ((job.get("payload") or {}).get("message") or "")
                if isinstance(jid, str) and DAG_RUNTIME_COMMAND in str(msg):
                    configured_jobs.append(jid)
                    dag_path = DAG_JOB_TO_DAG_PATH.get(jid)
                    if dag_path:
                        configured_dag_paths.append(dag_path)
                        full_dag_path = get_workspace_root() / dag_path
                        payload = _read_json(full_dag_path)
                        graph_id = (payload or {}).get("graph_id")
                        if isinstance(graph_id, str) and graph_id.strip():
                            configured_workflows.add(graph_id.strip())
    except (OSError, json.JSONDecodeError):
        pass
    if not configured_workflows:
        configured_workflows = set(
            graph_id
            for graph_id in (
                "fourclaw_auto_post_v1",
                "fourclaw_engage_v1",
                "moltbook_auto_post_v1",
                "moltbook_engage_v1",
                "aichan_auto_post_v1",
                "aichan_engage_v1",
                "agentchan_auto_post_v1",
                "agentchan_engage_v1",
                "job_search_degree_agnostic_agent_runtime_v1",
                "knowledge_research_auto_v1",
                "knowledge_research_auto_v2",
                "overseer_monitor_v1",
                "moltstack_draft_v1",
                "moltstack_publish_v1",
                "memory_maintenance_v1",
                "social_media_v1",
            )
        )
    return {
        "command": DAG_RUNTIME_COMMAND.strip(),
        "configured_jobs": configured_jobs,
        "configured_dag_paths": sorted(set(configured_dag_paths)),
        "configured_workflows": sorted(configured_workflows),
    }


def get_monitoring_insight(
    hours: int = 24,
    limit_runs: int = 200,
    dag_only: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).timestamp()
    window_start = now - (max(1, min(hours, 24 * 14)) * 3600)
    runtime = _load_dag_runtime_config()
    allowed_workflows = set(runtime.get("configured_workflows", []))
    apply_dag_filter = bool(dag_only)
    runs = list_index_runs(limit=max(1, min(limit_runs, 5000)))

    # Keep newest-to-oldest ordering from run index and filter to window.
    selected = []
    for r in runs:
        wf = r.get("graph_id") or "unknown"
        if apply_dag_filter and allowed_workflows and wf not in allowed_workflows:
            continue
        started = r.get("started_at")
        if isinstance(started, (int, float)) and started < window_start:
            continue
        selected.append(r)

    by_wf: dict[str, dict[str, Any]] = {}
    anomalies: list[dict[str, Any]] = []
    recent_runs: list[dict[str, Any]] = []

    for r in selected:
        run_id = r.get("run_id")
        wf = r.get("graph_id") or "unknown"
        run_dir_raw = r.get("run_dir")
        summary = None
        if isinstance(run_dir_raw, str) and run_dir_raw.strip():
            rd = Path(run_dir_raw)
            summary = _read_json(rd / "summary.json")
        final_status = (summary or {}).get("final_status")
        failed = _is_failed(r.get("status"), final_status)
        duration_s = _extract_duration_s(r)
        blocked_nodes = _extract_blocked_nodes(summary)
        policy_violations = _extract_policy_violations(summary)

        rec = {
            "run_id": run_id,
            "workflow_id": wf,
            "status": r.get("status") or final_status or "unknown",
            "duration_s": duration_s,
            "blocked_nodes": blocked_nodes,
            "policy_violations": policy_violations,
            "started_at": r.get("started_at"),
        }
        recent_runs.append(rec)

        row = by_wf.setdefault(
            wf,
            {
                "workflow_id": wf,
                "runs": 0,
                "failed_runs": 0,
                "durations": [],
                "blocked_nodes": 0,
                "policy_violations": 0,
            },
        )
        row["runs"] += 1
        row["failed_runs"] += 1 if failed else 0
        if duration_s is not None:
            row["durations"].append(duration_s)
        row["blocked_nodes"] += blocked_nodes
        row["policy_violations"] += policy_violations

        if policy_violations > 0:
            anomalies.append(
                {
                    "type": "policy_violation",
                    "run_id": run_id,
                    "workflow_id": wf,
                    "value": policy_violations,
                    "threshold": None,
                    "started_at": r.get("started_at"),
                }
            )

    for wf, row in by_wf.items():
        durations = sorted(row["durations"])
        if len(durations) >= 3:
            med = median(durations)
            abs_dev = [abs(d - med) for d in durations]
            mad = median(abs_dev)
            if mad > 0:
                for rec in recent_runs:
                    if rec["workflow_id"] != wf or rec["duration_s"] is None:
                        continue
                    robust_z = 0.6745 * (rec["duration_s"] - med) / mad
                    if robust_z > 3.5:
                        anomalies.append(
                            {
                                "type": "duration_outlier",
                                "run_id": rec["run_id"],
                                "workflow_id": wf,
                                "value": rec["duration_s"],
                                "threshold": round(med + (3.5 * mad / 0.6745), 3),
                                "started_at": rec["started_at"],
                            }
                        )
            else:
                fallback_threshold = med * 3 if med > 0 else None
                if fallback_threshold:
                    for rec in recent_runs:
                        if rec["workflow_id"] != wf or rec["duration_s"] is None:
                            continue
                        if rec["duration_s"] > fallback_threshold:
                            anomalies.append(
                                {
                                    "type": "duration_outlier",
                                    "run_id": rec["run_id"],
                                    "workflow_id": wf,
                                    "value": rec["duration_s"],
                                    "threshold": round(fallback_threshold, 3),
                                    "started_at": rec["started_at"],
                                }
                            )

        if row["runs"] >= 4:
            fail_rate = row["failed_runs"] / row["runs"]
            if fail_rate >= 0.5:
                anomalies.append(
                    {
                        "type": "failure_spike",
                        "run_id": None,
                        "workflow_id": wf,
                        "value": round(fail_rate, 3),
                        "threshold": 0.5,
                        "started_at": None,
                    }
                )

    by_workflow = []
    total_runs = 0
    total_failed = 0
    total_blocked = 0
    total_policy = 0
    for wf in sorted(by_wf.keys()):
        row = by_wf[wf]
        durations = sorted(row["durations"])
        runs = row["runs"]
        failed_runs = row["failed_runs"]
        fail_rate = (failed_runs / runs) if runs else 0.0
        avg_duration = (sum(durations) / len(durations)) if durations else None
        p95 = _percentile(durations, 0.95)
        outlier_runs = sum(1 for a in anomalies if a["type"] == "duration_outlier" and a["workflow_id"] == wf)
        by_workflow.append(
            {
                "workflow_id": wf,
                "runs": runs,
                "failed_runs": failed_runs,
                "fail_rate": round(fail_rate, 3),
                "avg_duration_s": round(avg_duration, 3) if avg_duration is not None else None,
                "p95_duration_s": round(p95, 3) if p95 is not None else None,
                "outlier_runs": outlier_runs,
                "blocked_nodes": row["blocked_nodes"],
                "policy_violations": row["policy_violations"],
            }
        )
        total_runs += runs
        total_failed += failed_runs
        total_blocked += row["blocked_nodes"]
        total_policy += row["policy_violations"]

    totals = {
        "runs": total_runs,
        "failed_runs": total_failed,
        "fail_rate": round((total_failed / total_runs), 3) if total_runs else 0.0,
        "blocked_nodes": total_blocked,
        "policy_violations": total_policy,
    }

    return {
        "ok": True,
        "window_hours": max(1, min(hours, 24 * 14)),
        "dag_only": bool(apply_dag_filter),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dag_runtime": runtime,
        "totals": totals,
        "by_workflow": by_workflow,
        "anomalies": anomalies[:200],
        "recent_runs": recent_runs[:100],
    }
