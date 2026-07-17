from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from hg_core.human_notifications import list_human_notifications
from hg_gateway.approval_service import ApprovalService
from .run_index_db import list_runs as list_runs_index


def _approval_href(*, task_name: str | None, approval_id: str) -> str:
    workflow_id = str(task_name or "").strip()
    query: list[str] = []
    if workflow_id:
        query.append(f"workflow_id={workflow_id}")
    if approval_id:
        query.append(f"approval_id={approval_id}")
    suffix = "&".join(query)
    return f"#/approvals{f'?{suffix}' if suffix else ''}"


def _approval_release_window(approval_row: dict[str, Any] | None) -> tuple[int | None, str | None, bool]:
    if not isinstance(approval_row, dict):
        return None, None, False
    preview = approval_row.get("preview_json") if isinstance(approval_row.get("preview_json"), dict) else {}
    raw_hours = preview.get("release_window_hours")
    if raw_hours in {None, ""}:
        return None, None, False
    try:
        hours = max(1, int(raw_hours))
    except (TypeError, ValueError):
        return None, None, False
    decided_at = str(approval_row.get("decided_at") or "").strip()
    if not decided_at:
        return hours, None, False
    try:
        decided_dt = datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
    except ValueError:
        return hours, None, False
    if decided_dt.tzinfo is None:
        decided_dt = decided_dt.replace(tzinfo=UTC)
    approved_until = decided_dt.astimezone(UTC) + timedelta(hours=hours)
    approved_until_iso = approved_until.isoformat().replace("+00:00", "Z")
    return hours, approved_until_iso, approved_until <= datetime.now(UTC)


def _parse_iso_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _build_followup_summary(
    *,
    root: Path,
    task_name: str,
    approval_id: str,
    decided_at: str | None,
    resolution_context: dict[str, Any] | None,
    latest_release_attempt: dict[str, Any] | None,
) -> dict[str, Any]:
    context = resolution_context if isinstance(resolution_context, dict) else {}
    expectation = str(context.get("followup_expectation") or "").strip()
    window_hours = _coerce_followup_window_hours(context.get("followup_window_hours"), 24)
    if not expectation:
        return {
            "expected": False,
            "observed": None,
            "expectation": None,
            "status": "none",
            "window_hours": None,
            "due_at": None,
            "last_observed_at": None,
            "observation_kind": None,
            "observation_detail": None,
        }
    decided_dt = _parse_iso_timestamp(decided_at)
    due_at = None
    overdue = False
    if decided_dt is not None and window_hours is not None:
        due_dt = decided_dt + timedelta(hours=window_hours)
        due_at = due_dt.isoformat().replace("+00:00", "Z")
        overdue = due_dt <= datetime.now(UTC)
    latest_observation: dict[str, Any] | None = None
    if decided_dt is not None:
        for row in list_human_notifications(root, limit=200):
            if not isinstance(row, dict):
                continue
            if str(row.get("task_name") or "").strip() != task_name:
                continue
            ts = _parse_iso_timestamp(row.get("timestamp"))
            if ts is None or ts <= decided_dt:
                continue
            kind = str(row.get("kind") or "").strip()
            if kind in {"review_handoff_resolution", "agency_gate"}:
                continue
            latest_observation = {
                "timestamp": row.get("timestamp"),
                "kind": kind or "notification",
                "detail": str(row.get("message") or "").strip() or None,
            }
            break
    if latest_observation is None and isinstance(latest_release_attempt, dict):
        release_status = str(latest_release_attempt.get("status") or "").strip().lower()
        release_ts = _parse_iso_timestamp(latest_release_attempt.get("timestamp"))
        if (
            release_ts is not None
            and (decided_dt is None or release_ts > decided_dt)
            and release_status not in {"blocked", "expired", "pending_approval"}
        ):
            latest_observation = {
                "timestamp": latest_release_attempt.get("timestamp"),
                "kind": str(latest_release_attempt.get("kind") or "release_attempt").strip() or "release_attempt",
                "detail": str(latest_release_attempt.get("message") or latest_release_attempt.get("reason") or "").strip() or None,
            }
    if latest_observation is None:
        return {
            "expected": True,
            "observed": False,
            "expectation": expectation,
            "status": "overdue" if overdue else "pending",
            "window_hours": window_hours,
            "due_at": due_at,
            "last_observed_at": None,
            "observation_kind": None,
            "observation_detail": None,
        }
    return {
        "expected": True,
        "observed": True,
        "expectation": expectation,
        "status": "observed",
        "window_hours": window_hours,
        "due_at": due_at,
        "last_observed_at": latest_observation.get("timestamp"),
        "observation_kind": latest_observation.get("kind"),
        "observation_detail": latest_observation.get("detail"),
    }


def _coerce_followup_window_hours(*values: Any) -> int | None:
    for raw in values:
        if raw in {None, ""}:
            continue
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            continue
    return None


def _summarize_node_trace(trace_timeline: Any) -> dict[str, Any]:
    rows = trace_timeline if isinstance(trace_timeline, list) else []
    counts = {"nodes": 0, "done": 0, "failed": 0, "blocked": 0, "running": 0, "pending": 0}
    latest_node: dict[str, Any] | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        counts["nodes"] += 1
        latest_node = row
        status = str(row.get("status") or "").strip().lower()
        if status in {"done", "completed", "succeeded", "success"}:
            counts["done"] += 1
        elif status in {"failed", "error"}:
            counts["failed"] += 1
        elif status == "blocked":
            counts["blocked"] += 1
        elif status == "running":
            counts["running"] += 1
        elif status in {"pending", "ready"}:
            counts["pending"] += 1
    return {
        "counts": counts,
        "latest_node_id": latest_node.get("node_id") if latest_node else None,
        "latest_node_status": latest_node.get("status") if latest_node else None,
        "latest_assigned_entity": latest_node.get("assigned_entity") if latest_node else None,
    }


def build_workflow_status_summary(
    root: Path | None,
    *,
    workflow_id: str | None = None,
    job_id: str | None = None,
    graph_id: str | None = None,
    launch_run_id: str | None = None,
    launch_status: str | None = None,
    launch_goal: str | None = None,
) -> dict[str, Any]:
    workflow_key = str(workflow_id or graph_id or job_id or "").strip() or None
    summary: dict[str, Any] = {
        "workflow_id": workflow_id or None,
        "job_id": job_id or None,
        "graph_id": graph_id or None,
        "status": "idle",
        "latest_run_id": None,
        "latest_run_status": None,
        "latest_run_started_at": None,
        "latest_run_ended_at": None,
        "latest_run_href": None,
        "activity_href": f"#/activity?{f'workflow_id={workflow_key}' if workflow_key else ''}".rstrip("?"),
        "node_state_summary": _summarize_node_trace([]),
        "trace_timeline": [],
        "audit_summary": {},
        "launch": None,
    }
    if root is not None:
        candidate_ids = {str(item).strip() for item in [workflow_id, graph_id, job_id] if str(item).strip()}
        latest_run: dict[str, Any] | None = None
        try:
            for row in list_runs_index(limit=500):
                if not isinstance(row, dict):
                    continue
                row_graph_id = str(row.get("graph_id") or "").strip()
                if row_graph_id and row_graph_id in candidate_ids:
                    latest_run = row
                    break
        except Exception:
            latest_run = None
        if latest_run:
            run_id = str(latest_run.get("run_id") or "").strip() or None
            summary.update(
                {
                    "status": str(latest_run.get("status") or "unknown"),
                    "latest_run_id": run_id,
                    "latest_run_status": str(latest_run.get("status") or "unknown"),
                    "latest_run_started_at": latest_run.get("started_at"),
                    "latest_run_ended_at": latest_run.get("ended_at"),
                    "latest_run_href": f"#/activity?run_id={run_id}" if run_id else None,
                }
            )
            run_dir_text = str(latest_run.get("run_dir") or "").strip()
            run_dir = Path(run_dir_text).expanduser() if run_dir_text else None
            trace_timeline: list[dict[str, Any]] = []
            audit_summary: dict[str, Any] = {}
            if run_dir and run_dir.exists():
                state_path = run_dir / "state.json"
                summary_path = run_dir / "summary.json"
                try:
                    if state_path.exists():
                        state = json.loads(state_path.read_text(encoding="utf-8"))
                        node_states = state.get("node_states") if isinstance(state, dict) else {}
                        if isinstance(node_states, dict):
                            for node_id, node_blob in node_states.items():
                                if not isinstance(node_blob, dict):
                                    continue
                                trace_timeline.append(
                                    {
                                        "node_id": str(node_blob.get("id") or node_id),
                                        "node_type": node_blob.get("type"),
                                        "assigned_entity": node_blob.get("assigned_entity"),
                                        "status": node_blob.get("status"),
                                        "attempt_count": node_blob.get("attempt_count"),
                                        "started_at": node_blob.get("started_at"),
                                        "ended_at": node_blob.get("ended_at"),
                                        "duration_ms": node_blob.get("duration_ms"),
                                        "error": node_blob.get("error"),
                                    }
                                )
                        trace_timeline.sort(key=lambda row: str(row.get("started_at") or ""))
                except Exception:
                    trace_timeline = []
                try:
                    if summary_path.exists():
                        loaded = json.loads(summary_path.read_text(encoding="utf-8"))
                        if isinstance(loaded, dict):
                            audit_summary = loaded
                except Exception:
                    audit_summary = {}
            summary["trace_timeline"] = trace_timeline[:12]
            summary["audit_summary"] = audit_summary
            summary["node_state_summary"] = _summarize_node_trace(trace_timeline)
    if launch_run_id:
        summary["launch"] = {
            "run_id": launch_run_id,
            "status": launch_status,
            "goal": launch_goal,
        }
        if not summary.get("latest_run_id"):
            summary["latest_run_id"] = launch_run_id
            summary["latest_run_status"] = launch_status
            summary["latest_run_href"] = f"#/activity?run_id={launch_run_id}"
            summary["status"] = launch_status or summary.get("status") or "queued"
    return summary


def _review_handoff_rows(root: Path) -> list[dict[str, Any]]:
    latest_release_attempt_by_approval: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for row in list_human_notifications(root, limit=500):
        if not isinstance(row, dict):
            continue
        summary = row.get("summary")
        if not isinstance(summary, dict):
            continue
        review_handoff = summary.get("review_handoff")
        if not isinstance(review_handoff, dict):
            continue
        approval_id = str(review_handoff.get("approval_id") or "").strip()
        if not approval_id:
            continue
        execution = summary.get("execution") if isinstance(summary.get("execution"), dict) else {}
        blocked_reason = str(execution.get("blocked_reason") or "").strip()
        kind = str(row.get("kind") or "").strip()
        if approval_id not in latest_release_attempt_by_approval and (
            kind == "review_handoff_release_expired"
            or blocked_reason.startswith("approval_release_")
            or blocked_reason == "approval_expired"
        ):
            latest_release_attempt_by_approval[approval_id] = {
                "timestamp": row.get("timestamp"),
                "status": execution.get("status") or review_handoff.get("status"),
                "reason": blocked_reason or review_handoff.get("status"),
                "message": row.get("message"),
                "kind": kind,
            }
        if kind != "agency_gate":
            continue
        agency_control = summary.get("agency_control") if isinstance(summary.get("agency_control"), dict) else {}
        approval_status = None
        decided_at = None
        decided_by = None
        decision_note = None
        resolution_context = {}
        refreshed_from_approval_id = None
        refresh_note = None
        refreshed_by = None
        refresh_reason_codes: list[str] = []
        try:
            approval_row = ApprovalService().get_request(approval_id, tenant_id="default")
        except Exception:
            approval_row = None
        if isinstance(approval_row, dict):
            approval_status = approval_row.get("status")
            decided_at = approval_row.get("decided_at")
            decided_by = approval_row.get("decided_by")
            decision_note = approval_row.get("decision_note")
            approval_preview = approval_row.get("preview_json") if isinstance(approval_row.get("preview_json"), dict) else {}
            resolution_context = approval_preview.get("resolution_context") if isinstance(approval_preview.get("resolution_context"), dict) else {}
            refresh_context = approval_preview.get("refresh_context") if isinstance(approval_preview.get("refresh_context"), dict) else {}
            refreshed_from_approval_id = str(
                refresh_context.get("from_approval_id")
                or approval_preview.get("refreshed_from_approval_id")
                or review_handoff.get("refreshed_from_approval_id")
                or ""
            ).strip() or None
            refresh_note = str(
                refresh_context.get("note")
                or approval_preview.get("refresh_note")
                or review_handoff.get("refresh_note")
                or ""
            ).strip() or None
            refreshed_by = str(
                refresh_context.get("refreshed_by")
                or approval_preview.get("refreshed_by")
                or review_handoff.get("refreshed_by")
                or ""
            ).strip() or None
            raw_refresh_reason_codes = (
                refresh_context.get("reason_codes")
                or approval_preview.get("refresh_reason_codes")
                or review_handoff.get("refresh_reason_codes")
                or []
            )
            if isinstance(raw_refresh_reason_codes, list):
                refresh_reason_codes = [str(code).strip() for code in raw_refresh_reason_codes if str(code).strip()]
        release_window_hours, approved_until, approval_expired = _approval_release_window(approval_row)
        followup_summary = _build_followup_summary(
            root=root,
            task_name=str(row.get("task_name") or "").strip(),
            approval_id=approval_id,
            decided_at=decided_at,
            resolution_context=resolution_context,
            latest_release_attempt=latest_release_attempt_by_approval.get(approval_id),
        )
        rows.append(
            {
                "timestamp": row.get("timestamp"),
                "task_name": row.get("task_name"),
                "operational_agent_id": row.get("operational_agent_id"),
                "approval_id": approval_id,
                "approval_href": _approval_href(task_name=row.get("task_name"), approval_id=approval_id),
                "draft_artifact": review_handoff.get("draft_artifact"),
                "title": review_handoff.get("title"),
                "status": approval_status or execution.get("status"),
                "release_window_hours": release_window_hours,
                "approved_until": approved_until,
                "approval_expired": approval_expired,
                "blocked_reason": execution.get("blocked_reason"),
                "reason": agency_control.get("reason"),
                "message": row.get("message"),
                "decided_at": decided_at,
                "decided_by": decided_by,
                "decision_note": decision_note,
                "resolution_context": resolution_context,
                "refreshed_from_approval_id": refreshed_from_approval_id,
                "refresh_note": refresh_note,
                "refreshed_by": refreshed_by,
                "refresh_reason_codes": refresh_reason_codes,
                "latest_release_attempt": latest_release_attempt_by_approval.get(approval_id),
                "followup_summary": followup_summary,
            }
        )
    return rows


def build_review_handoff_summary(
    root: Path | None,
    *,
    task_names: list[str] | None = None,
    workflow_id: str | None = None,
    job_id: str | None = None,
    graph_id: str | None = None,
    operational_agent_id: str | None = None,
    agency_control_summary: dict[str, Any] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
    operational_resume_governance_summary: dict[str, Any] | None = None,
    operational_resume_checkpoint: dict[str, Any] | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    if root is None:
        return {"count": 0, "pending_count": 0, "items": [], "latest": None}
    task_set = {str(task).strip() for task in (task_names or []) if str(task).strip()}
    operational_key = str(operational_agent_id or "").strip()
    matches: list[dict[str, Any]] = []
    for row in _review_handoff_rows(root):
        row_task = str(row.get("task_name") or "").strip()
        row_operational = str(row.get("operational_agent_id") or "").strip()
        if task_set and row_task in task_set:
            matches.append(row)
        elif operational_key and row_operational == operational_key:
            matches.append(row)
        if len(matches) >= max(1, limit):
            break
    agency_control_summary = agency_control_summary if isinstance(agency_control_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    operational_resume_governance_summary = (
        operational_resume_governance_summary if isinstance(operational_resume_governance_summary, dict) else {}
    )
    operational_resume_checkpoint = operational_resume_checkpoint if isinstance(operational_resume_checkpoint, dict) else {}
    effective_mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    release_blockers: list[str] = []
    if effective_mode == "held":
        release_blockers.append("agency_hold")
    if bool(agency_control_summary.get("outbound_budget_exhausted")):
        release_blockers.append("outbound_budget")
    outbound_lane_policy = str(agency_control_summary.get("outbound_lane_policy") or "unrestricted").strip().lower()
    if outbound_lane_policy in {"drafts_only", "blocked"}:
        release_blockers.append(f"lane_policy:{outbound_lane_policy}")
    continuity_status = str(continuity_recovery_readiness.get("status") or "").strip().lower()
    if continuity_status == "blocked":
        release_blockers.append("continuity_recovery")
    elif continuity_status == "caution" and not bool(continuity_recovery_readiness.get("resume_permitted")):
        release_blockers.append("continuity_recovery_ack_required")
    resume_status = str(operational_resume_governance_summary.get("status") or "").strip().lower()
    if resume_status == "ready" and not bool(operational_resume_checkpoint.get("approved")):
        release_blockers.append("operational_resume_checkpoint_required")
    release_ready = not release_blockers
    for row in matches:
        row_blockers = list(release_blockers)
        if bool(row.get("approval_expired")):
            row_blockers.append("approval_expired")
        row["release_ready"] = release_ready
        row["release_ready"] = not row_blockers
        row["release_blockers"] = row_blockers
        row["release_next_eligible_at"] = agency_control_summary.get("outbound_budget_next_reset_at") or row.get("approved_until")
        latest_release_attempt = row.get("latest_release_attempt") if isinstance(row.get("latest_release_attempt"), dict) else {}
        refresh_reasons: list[str] = []
        status = str(row.get("status") or "").strip().lower()
        followup_summary = row.get("followup_summary") if isinstance(row.get("followup_summary"), dict) else {}
        if status in {"approved", "rejected", "request_edit"}:
            refresh_reasons.append(f"status:{status}")
        if bool(row.get("approval_expired")):
            refresh_reasons.append("approval_expired")
        if str(followup_summary.get("status") or "").strip().lower() == "overdue":
            refresh_reasons.append("followup_overdue")
        release_reason = str(latest_release_attempt.get("reason") or "").strip()
        if release_reason in {
            "approval_expired",
            "approval_release_held",
            "approval_release_lane_policy_blocked",
            "approval_release_outbound_budget_exhausted",
        }:
            refresh_reasons.append(release_reason)
        row["refresh_recommended"] = bool(refresh_reasons) and status != "pending_approval"
        row["refresh_reasons"] = refresh_reasons
    pending_count = sum(1 for item in matches if str(item.get("status") or "").strip() == "pending_approval")
    any_expired = any(bool(item.get("approval_expired")) for item in matches)
    summary_blockers = list(release_blockers)
    if any_expired:
        summary_blockers.append("approval_expired")
    latest = matches[0] if matches else None
    workflow_status_summary = build_workflow_status_summary(
        root,
        workflow_id=workflow_id,
        job_id=job_id,
        graph_id=graph_id,
    )
    return {
        "count": len(matches),
        "pending_count": pending_count,
        "release_ready": not summary_blockers,
        "release_blockers": summary_blockers,
        "release_next_eligible_at": agency_control_summary.get("outbound_budget_next_reset_at") or (matches[0].get("approved_until") if matches else None),
        "refresh_recommended": bool((latest or {}).get("refresh_recommended")),
        "refresh_reasons": (latest or {}).get("refresh_reasons") or [],
        "items": matches,
        "latest": latest,
        "workflow_status_summary": workflow_status_summary,
    }
