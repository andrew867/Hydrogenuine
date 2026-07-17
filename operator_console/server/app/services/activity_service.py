"""
Recent activity: runs, decisions across entities, optional overseer state.
"""

import json
import math
import os
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from hg_core.human_notifications import list_human_notifications
from hg_gateway.events_ledger import list_events
from hg_gateway.shared_storage import (
    get_latest_overseer_state,
    list_agent_decisions,
    list_overseer_timeseries,
)
from hg_gateway.events_ledger import list_evidence
from .evidence_timeline_summary import build_evidence_timeline_summary
from .drift_review_summary import get_recent_drift_timeline_events


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _get_registry() -> dict[str, dict[str, Any]]:
    try:
        from hg_core.job_registry import get_registry
        return get_registry()
    except Exception:
        return {}


def _runtime_tenant_id() -> str:
    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def get_recent_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Last N runs from run index."""
    try:
        from ..services.run_index_db import list_runs
        rows = list_runs(limit=limit)
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_recent_decisions(limit: int = 20) -> list[dict[str, Any]]:
    """Last N decisions across all entities, sorted by timestamp desc."""
    root = _workspace_root()
    registry = _get_registry()
    if not root or not registry:
        return []
    collected: list[tuple[str, dict]] = []
    for task_name, info in registry.items():
        session_target = info.get("session_target")
        if not session_target:
            continue
        agent_id = session_target.replace("automation-", "", 1) if str(session_target).startswith("automation-") else str(session_target)
        shared_decisions = list_agent_decisions(agent_id, limit=limit * 4)
        for d in shared_decisions:
            ts = d.get("timestamp") or ""
            collected.append((ts, {"entity": task_name, **d}))
    collected.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in collected[:limit]]


def get_recent_human_notifications(limit: int = 20) -> list[dict[str, Any]]:
    root = _workspace_root()
    if not root:
        return []
    items = list_human_notifications(root, limit=limit)
    parsed: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        review_release_state = _review_release_state(row.get("task_name"), summary)
        parsed.append(
            {
                "timestamp": row.get("timestamp"),
                "task_name": row.get("task_name"),
                "kind": row.get("kind"),
                "message": row.get("message"),
                "transport": row.get("transport"),
                "recipient": row.get("recipient"),
                "social_account_id": row.get("social_account_id"),
                "operational_agent_id": row.get("operational_agent_id"),
                "summary": summary,
                "governance_label": _governance_label(row.get("kind"), summary),
                "governance_detail": _governance_detail(summary),
                "approval_href": _approval_href(row.get("task_name"), summary),
                "review_release_state": review_release_state,
                "governance_actions": _governance_actions(row, summary),
            }
        )
    return parsed


def get_recent_support_claims(limit: int = 20) -> list[dict[str, Any]]:
    tenant_id = _runtime_tenant_id()
    try:
        rows = list_evidence(tenant_id, evidence_types=["support_claim"], limit=limit)
    except Exception:
        return []
    parsed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        content_ref = row.get("content_ref")
        claim: dict[str, Any] = {}
        if isinstance(content_ref, str) and content_ref.strip():
            try:
                loaded = json.loads(content_ref)
                if isinstance(loaded, dict):
                    claim = loaded
            except Exception:
                claim = {}
        parsed.append(
            {
                "ledger_id": row.get("ledger_id"),
                "timestamp": row.get("ts"),
                "approval_id": row.get("approval_id"),
                "action": str(claim.get("decision") or claim.get("action") or "support_claim").strip(),
                "rationale": str(claim.get("decision_note") or claim.get("rationale") or "").strip() or None,
                "outcome": str(claim.get("decision") or "").strip() or None,
                "entity_id": claim.get("entity_id"),
                "workflow_id": claim.get("workflow_id"),
                "target_platform": claim.get("target_platform"),
                "decision_note": claim.get("decision_note"),
                "decided_by": claim.get("decided_by"),
            }
        )
    return parsed


def _timeline_event_title(event_type: Any, payload: dict[str, Any]) -> str:
    normalized = str(event_type or "").strip().lower()
    if normalized == "chat.create":
        return "Chat created"
    if normalized == "chat.rename":
        return "Chat renamed"
    if normalized == "chat.archive":
        return "Chat archived"
    if normalized == "chat.trash":
        return "Chat trashed"
    if normalized == "chat.restore":
        return "Chat restored"
    if normalized == "turn.start":
        return "Turn started"
    if normalized == "turn.end":
        return "Turn completed"
    if normalized == "message.final":
        return "Turn completed"
    if normalized == "approval.create":
        return "Approval created"
    if normalized == "approval.resolve":
        return "Approval resolved"
    if normalized == "swarm.run.start":
        return "Swarm started"
    if normalized == "swarm.run.end":
        return "Swarm completed"
    if normalized == "swarm.archive":
        return "Swarm archived"
    if normalized == "swarm.trash":
        return "Swarm trashed"
    if normalized == "swarm.restore":
        return "Swarm restored"
    if normalized == "proof.run.start":
        return "Proof run started"
    if normalized == "proof.run.end":
        return "Proof run completed"
    if normalized == "drift.detected":
        return "Drift detected"
    if normalized == "reflection.artifact.promoted":
        return "Reflection promoted"
    if normalized == "reflection.artifact.discarded":
        return "Reflection discarded"
    if normalized == "reflection.artifact.escalated":
        return "Reflection escalated"
    if normalized == "timeline.event.recorded":
        return "Timeline event recorded"
    if normalized == "drift.detected":
        return "Drift detected"
    action = str(payload.get("action") or "").strip()
    if action:
        return action.replace("_", " ").strip().title()
    return normalized.replace(".", " ").replace("_", " ").strip().title() or "Timeline event"


def _timeline_event_detail(event_type: Any, payload: dict[str, Any]) -> str | None:
    normalized = str(event_type or "").strip().lower()
    candidates = [
        payload.get("title"),
        payload.get("detail"),
        payload.get("reason"),
        payload.get("message"),
        payload.get("decision"),
        payload.get("blocked_reason"),
        payload.get("workflow_id"),
        payload.get("run_id"),
        payload.get("chat_id"),
        payload.get("approval_id"),
    ]
    if normalized == "approval.resolve":
        decision = str(payload.get("decision") or "").strip()
        approval_id = str(payload.get("approval_id") or "").strip()
        if decision and approval_id:
            return f"{decision} · {approval_id}"
    if normalized == "drift.detected":
        severity = str(payload.get("severity") or "").strip()
        summary = str(payload.get("summary") or "").strip()
        if severity and summary:
            return f"{severity} · {summary}"
        if summary:
            return summary
    if normalized.startswith("reflection.artifact."):
        note = str(payload.get("note") or payload.get("detail") or "").strip()
        if note:
            return note
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def get_recent_timeline_events(
    limit: int = 20,
    *,
    entity_id: str | None = None,
    chat_id: str | None = None,
    run_id: str | None = None,
    workflow_id: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> list[dict[str, Any]]:
    tenant_id = _runtime_tenant_id()
    try:
        rows = list_events(
            tenant_id,
            run_id=run_id,
            chat_id=chat_id,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=max(limit * 4, limit),
        )
    except Exception:
        return []

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload: dict[str, Any] = {}
        try:
            raw = row.get("payload_json")
            if isinstance(raw, str) and raw.strip():
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    payload = loaded
        except Exception:
            payload = {}
        candidate_entity_id = str(payload.get("entity_id") or row.get("actor_id") or "").strip()
        candidate_workflow_id = str(payload.get("workflow_id") or payload.get("task_name") or row.get("run_id") or "").strip()
        if entity_id and entity_id.strip() and entity_id.strip() not in {candidate_entity_id, str(row.get("chat_id") or "").strip(), str(row.get("run_id") or "").strip()}:
            continue
        if workflow_id and workflow_id.strip() and workflow_id.strip() not in {candidate_workflow_id, str(row.get("run_id") or "").strip()}:
            continue
        title = _timeline_event_title(row.get("event_type"), payload)
        detail = _timeline_event_detail(row.get("event_type"), payload)
        message_id = str(payload.get("message_id") or "").strip() or None
        provenance_href = None
        if message_id and row.get("chat_id"):
            provenance_href = f"#/chat/{row.get('chat_id')}?message_id={message_id}"
        event_name = str(row.get("event_type") or "").strip().lower()
        if event_name.startswith("reflection.artifact.") and payload.get("artifact_id"):
            provenance_href = f"#/reflections?artifact_id={payload.get('artifact_id')}"
        if event_name == "drift.detected" and payload.get("root_id"):
            provenance_href = f"#/governance?root_id={payload.get('root_id')}"
        href = provenance_href if event_name.startswith("reflection.artifact.") and provenance_href else (
            f"#/approvals?approval_id={row.get('approval_id')}"
            if str(row.get("event_type") or "").strip().lower().startswith("approval.") and row.get("approval_id")
            else (f"#/chat/{row.get('chat_id')}" if row.get("chat_id") else None)
        )
        if event_name == "drift.detected" and provenance_href:
            href = provenance_href
        normalized.append(
            {
                "event_id": row.get("event_id"),
                "timestamp": row.get("ts"),
                "entity_id": candidate_entity_id or None,
                "chat_id": row.get("chat_id"),
                "run_id": row.get("run_id"),
                "workflow_id": candidate_workflow_id or None,
                "approval_id": row.get("approval_id"),
                "event_type": row.get("event_type"),
                "message_id": message_id,
                "title": title,
                "detail": detail,
                "href": href,
                "provenance_href": provenance_href,
                "payload": payload,
            }
        )
    for row in get_recent_drift_timeline_events(limit=max(limit, 20), entity_id=entity_id, workflow_id=workflow_id):
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "event_id": row.get("event_id"),
                "timestamp": row.get("timestamp"),
                "entity_id": row.get("entity_id"),
                "chat_id": None,
                "run_id": None,
                "workflow_id": row.get("workflow_id"),
                "approval_id": None,
                "event_type": "drift.detected",
                "message_id": None,
                "title": row.get("title") or "Drift detected",
                "detail": row.get("detail"),
                "href": row.get("href"),
                "provenance_href": row.get("href"),
                "payload": row.get("payload") or {},
            }
        )
    normalized.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    return normalized[:limit]


def _approval_href(task_name: Any, summary: dict[str, Any]) -> str | None:
    review_handoff = summary.get("review_handoff") if isinstance(summary.get("review_handoff"), dict) else {}
    approval_id = str(review_handoff.get("approval_id") or "").strip()
    workflow_id = str(task_name or "").strip()
    if not approval_id:
        return None
    query: list[str] = []
    if workflow_id:
        query.append(f"workflow_id={workflow_id}")
    query.append(f"approval_id={approval_id}")
    return f"#/approvals?{'&'.join(query)}"


def _governance_label(kind: Any, summary: dict[str, Any]) -> str | None:
    normalized = str(kind or "").strip()
    execution = summary.get("execution") if isinstance(summary.get("execution"), dict) else {}
    blocked_reason = str(execution.get("blocked_reason") or "").strip()
    labels = {
        "agency_gate": {
            "approval_release_operational_resume_checkpoint_required": "Resume approval required",
            "approval_release_continuity_recovery_ack_required": "Recovery acknowledgment required",
            "approval_release_continuity_recovery_blocked": "Continuity recovery blocked",
            "approval_release_outbound_budget_exhausted": "Outbound budget exhausted",
            "approval_release_lane_policy_blocked": "Lane policy blocked",
            "approval_release_held": "Agency hold",
            "review_handoff_refreshed": "Review handoff refreshed",
            "agency_control_review_only": "Review-only handoff",
        },
        "continuity_recovery_ack": "Recovery acknowledged",
        "continuity_runtime_observed": "Continuity observed in runtime",
        "post_rebuild_continuity_required": "Rebuild verification required",
        "post_rebuild_continuity_verified": "Rebuild verified",
        "post_rebuild_runtime_observed": "Post-rebuild runtime observed",
        "identity_restore_runtime_observed": "Post-restore runtime observed",
        "supervised_resume_runtime_observed": "Supervised resume observed",
        "operational_resume_checkpoint": "Resume approved",
        "operational_resume_checkpoint_invalidated": "Resume approval invalidated",
        "identity_resume_closeout": "Identity recovery closed out",
        "review_handoff_resolution": "Review decision recorded",
        "review_handoff_release_expired": "Review release expired",
        "commitment_recorded": "Commitment recorded",
        "commitment_fulfilled": "Commitment fulfilled",
        "commitment_expired": "Commitment expired",
    }
    if normalized == "agency_gate":
        return labels["agency_gate"].get(blocked_reason) or "Agency gate"
    value = labels.get(normalized)
    if isinstance(value, str):
        return value
    return None


def _governance_detail(summary: dict[str, Any]) -> str | None:
    if not isinstance(summary, dict):
        return None
    execution = summary.get("execution") if isinstance(summary.get("execution"), dict) else {}
    review_handoff = summary.get("review_handoff") if isinstance(summary.get("review_handoff"), dict) else {}
    agency_control = summary.get("agency_control") if isinstance(summary.get("agency_control"), dict) else {}
    continuity_recovery = summary.get("continuity_recovery") if isinstance(summary.get("continuity_recovery"), dict) else {}
    post_rebuild = summary.get("post_rebuild_continuity_check") if isinstance(summary.get("post_rebuild_continuity_check"), dict) else {}
    checkpoint = summary.get("operational_resume_checkpoint") if isinstance(summary.get("operational_resume_checkpoint"), dict) else {}
    parts: list[str] = []
    if review_handoff.get("approval_id"):
        parts.append(f"approval {review_handoff['approval_id']}")
    if agency_control.get("reason"):
        parts.append(str(agency_control.get("reason")))
    if continuity_recovery.get("cautions"):
        cautions = [str(item).strip() for item in continuity_recovery.get("cautions") or [] if str(item).strip()]
        if cautions:
            parts.append(", ".join(cautions))
    if post_rebuild.get("status"):
        parts.append(f"rebuild {post_rebuild['status']}")
    if checkpoint.get("invalidated_reason"):
        parts.append(str(checkpoint.get("invalidated_reason")))
    if execution.get("blocked_reason") and not parts:
        parts.append(str(execution.get("blocked_reason")))
    return " | ".join(parts[:3]) or None


def _review_release_state(task_name: Any, summary: dict[str, Any]) -> dict[str, Any] | None:
    review_handoff = summary.get("review_handoff") if isinstance(summary.get("review_handoff"), dict) else {}
    approval_id = str(review_handoff.get("approval_id") or "").strip()
    if not approval_id:
        return None
    try:
        from ..api.approvals_entity import _service as entity_approval_service, _enrich_review_release_state
    except Exception:
        return None
    try:
        entity_row = entity_approval_service().get_request(approval_id, tenant_id=_runtime_tenant_id())
    except Exception:
        entity_row = None
    if not isinstance(entity_row, dict):
        return None
    enriched = _enrich_review_release_state(entity_row)
    if not isinstance(enriched, dict):
        return None
    release_state = enriched.get("review_release_state")
    return release_state if isinstance(release_state, dict) else None


def _governance_actions(row: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict) or not isinstance(summary, dict):
        return None
    review_release_state = _review_release_state(row.get("task_name"), summary)
    execution = summary.get("execution") if isinstance(summary.get("execution"), dict) else {}
    continuity_recovery = summary.get("continuity_recovery") if isinstance(summary.get("continuity_recovery"), dict) else {}
    post_rebuild = summary.get("post_rebuild_continuity_check") if isinstance(summary.get("post_rebuild_continuity_check"), dict) else {}
    blocked_reason = str(execution.get("blocked_reason") or "").strip()
    release_blockers = list(review_release_state.get("release_blockers") or []) if isinstance(review_release_state, dict) else []
    platform = str(
        (review_release_state or {}).get("platform")
        or execution.get("platform")
        or row.get("platform")
        or ""
    ).strip()
    operational_agent_id = str(
        row.get("operational_agent_id")
        or execution.get("operational_agent_id")
        or (review_release_state or {}).get("operational_agent_id")
        or ""
    ).strip()
    continuity_recovery = (
        review_release_state.get("continuity_recovery_readiness")
        if isinstance(review_release_state, dict) and isinstance(review_release_state.get("continuity_recovery_readiness"), dict)
        else continuity_recovery
    )
    post_rebuild = (
        review_release_state.get("post_rebuild_continuity_check")
        if isinstance(review_release_state, dict) and isinstance(review_release_state.get("post_rebuild_continuity_check"), dict)
        else post_rebuild
    )
    actions = {
        "platform": platform or None,
        "operational_agent_id": operational_agent_id or None,
        "can_approve_resume": (
            "operational_resume_checkpoint_required" in release_blockers
            or blocked_reason == "approval_release_operational_resume_checkpoint_required"
        ),
        "can_acknowledge_recovery": (
            ("continuity_recovery_ack_required" in release_blockers or blocked_reason == "approval_release_continuity_recovery_ack_required")
            and bool(continuity_recovery.get("can_acknowledge"))
            and not bool(continuity_recovery.get("acknowledged"))
        ),
        "can_verify_rebuild": (
            ("verify_rebuild" == str((review_release_state or {}).get("required_next_action") or "").strip())
            or (
                str(row.get("kind") or "").strip() == "post_rebuild_continuity_required"
            and bool(post_rebuild.get("verification_required"))
            and not bool(post_rebuild.get("verified"))
            )
        ),
    }
    if not actions["platform"] or not actions["operational_agent_id"]:
        if actions["can_approve_resume"] or actions["can_acknowledge_recovery"] or actions["can_verify_rebuild"]:
            return None
    if not actions["can_approve_resume"] and not actions["can_acknowledge_recovery"] and not actions["can_verify_rebuild"]:
        return None
    return actions


def get_overseer_summary() -> dict[str, Any] | None:
    """Overseer latest_state and optional timeseries count."""
    root = _workspace_root()
    if not root:
        return None
    out: dict[str, Any] = {"latest_state": None, "timeseries_count_24h": None, "analysis_capabilities": None}
    latest_state = get_latest_overseer_state()
    if latest_state:
        out["latest_state"] = _compact_latest_state(latest_state)
        if isinstance(latest_state, dict) and isinstance(latest_state.get("analysis_capabilities"), dict):
            out["analysis_capabilities"] = latest_state.get("analysis_capabilities")
    timeseries = list_overseer_timeseries(hours=24, limit=10000)
    if timeseries:
        out["timeseries_count_24h"] = len(timeseries)
    return out


def _compact_latest_state(value: Any, depth: int = 0) -> Any:
    """Keep a bounded, UI-safe summary of latest_state to prevent heavy payloads."""
    if isinstance(value, str):
        return value[:400]
    if depth > 2:
        if isinstance(value, dict):
            simple_keys = list(value.keys())
            if len(simple_keys) <= 4 and all(not isinstance(value.get(key), (dict, list)) for key in simple_keys):
                return {str(key): _compact_latest_state(value.get(key), depth + 1) for key in simple_keys}
            return {"_truncated": True, "keys": list(value.keys())[:8]}
        if isinstance(value, list):
            return [{"_truncated": True, "count": len(value)}]
        return value
    if isinstance(value, dict):
        preferred_keys = (
            "run_id",
            "graph_id",
            "status",
            "final_status",
            "updated_at",
            "started_at",
            "counts",
            "budget_used",
        )
        out: dict[str, Any] = {}
        for key in preferred_keys:
            if key in value:
                out[key] = _compact_latest_state(value.get(key), depth + 1)
        # Keep a few additional keys for context but cap breadth.
        extras = [k for k in value.keys() if k not in out][:8]
        for key in extras:
            out[str(key)] = _compact_latest_state(value.get(key), depth + 1)
        return out
    if isinstance(value, list):
        return [_compact_latest_state(v, depth + 1) for v in value[:12]]
    return value


def get_dashboard_data(hours: int = 24) -> dict[str, Any]:
    """Dashboard: latest_state + timeseries entries from last N hours (for Status/Dashboard page charts)."""
    root = _workspace_root()
    out: dict[str, Any] = {"latest_state": None, "timeseries": [], "summary": get_overseer_summary(), "pdf_dashboard": {}, "analysis_capabilities": None}
    if not root:
        return out
    latest_state = get_latest_overseer_state()
    out["latest_state"] = _compact_latest_state(latest_state) if latest_state is not None else None
    if isinstance(out["latest_state"], dict) and isinstance(out["latest_state"].get("analysis_capabilities"), dict):
        out["analysis_capabilities"] = out["latest_state"].get("analysis_capabilities")
    out["timeseries"] = list_overseer_timeseries(hours=hours, limit=500)
    out["pdf_dashboard"] = _build_pdf_dashboard_summary(out.get("timeseries") or [])
    if out.get("analysis_capabilities") is None:
        out["analysis_capabilities"] = (out.get("summary") or {}).get("analysis_capabilities")
    return _json_safe(out)


def _overseer_dir() -> Path | None:
    root = _workspace_root()
    if not root:
        return None
    return root / "memory" / "overseer"


def _is_allowed_report_name(name: str) -> bool:
    lowered = name.lower()
    if ".." in name or "/" in name or "\\" in name:
        return False
    if not lowered.startswith("dashboard"):
        return False
    return lowered.endswith(".pdf") or lowered.endswith(".png")


def resolve_dashboard_report_path(report_ref: str) -> Path | None:
    base = _overseer_dir()
    if not base or not report_ref:
        return None
    report_ref = str(report_ref).strip()
    if report_ref.startswith("history/"):
        name = report_ref[len("history/") :]
        if not _is_allowed_report_name(name):
            return None
        path = base / "history" / name
        return path if path.exists() else None
    if not _is_allowed_report_name(report_ref):
        return None
    path = base / report_ref
    return path if path.exists() else None


def get_dashboard_reports(limit: int = 20) -> dict[str, Any]:
    base = _overseer_dir()
    out: dict[str, Any] = {"latest_pdf": None, "latest_png": None, "items": []}
    if not base or not base.exists():
        return out

    items: list[dict[str, Any]] = []

    def _append(path: Path, ref: str, source: str) -> None:
        try:
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            kind = "png" if path.suffix.lower() == ".png" else "pdf"
            items.append(
                {
                    "ref": ref,
                    "name": path.name,
                    "source": source,
                    "kind": kind,
                    "size": stat.st_size,
                    "modified_at": modified,
                }
            )
        except OSError:
            return

    for path in base.glob("dashboard*.pdf"):
        _append(path, path.name, "root")
    png_path = base / "dashboard.png"
    if png_path.exists():
        _append(png_path, "dashboard.png", "root")
    history = base / "history"
    if history.exists():
        for path in history.glob("dashboard*.pdf"):
            _append(path, f"history/{path.name}", "history")

    items.sort(key=lambda row: row.get("modified_at") or "", reverse=True)
    out["items"] = items[: max(1, limit)]
    for row in out["items"]:
        if row.get("kind") == "pdf" and out["latest_pdf"] is None:
            out["latest_pdf"] = row
        if row.get("kind") == "png" and out["latest_png"] is None:
            out["latest_png"] = row
    return out


def _build_pdf_dashboard_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(entries, list):
        entries = []
    agents_seen: set[str] = set()
    mode_counts: dict[str, int] = {}
    violation_trend: list[dict[str, Any]] = []
    budget_trend: list[dict[str, Any]] = []
    latest_timestamp = None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            latest_timestamp = timestamp

        violation_count = 0
        agents = entry.get("agents")
        if isinstance(agents, dict):
            for agent_id, agent_data in agents.items():
                if isinstance(agent_id, str) and agent_id:
                    agents_seen.add(agent_id)
                if not isinstance(agent_data, dict):
                    continue
                mode = str(agent_data.get("mode") or "normal")
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
                violations = agent_data.get("violations")
                if isinstance(violations, list):
                    violation_count += len(violations)

        budgets = entry.get("budgets") if isinstance(entry.get("budgets"), dict) else {}
        chaos = budgets.get("chaos") if isinstance(budgets.get("chaos"), dict) else {}
        credibility = budgets.get("credibility") if isinstance(budgets.get("credibility"), dict) else {}
        chaos_remaining = chaos.get("remaining", budgets.get("chaos_remaining"))
        cred_earned = credibility.get("earned", budgets.get("credibility_earned"))

        violation_trend.append({"timestamp": timestamp, "violations": violation_count})
        budget_trend.append(
            {
                "timestamp": timestamp,
                "chaos_remaining": chaos_remaining if isinstance(chaos_remaining, (int, float)) else None,
                "credibility_earned": cred_earned if isinstance(cred_earned, (int, float)) else None,
            }
        )

    return {
        "cycles_in_window": len(entries),
        "agents_observed": len(agents_seen),
        "latest_timestamp": latest_timestamp,
        "mode_distribution": mode_counts,
        "violation_trend": violation_trend[-240:],
        "budget_trend": budget_trend[-240:],
    }


def _is_wake_anchor_event(event_type: Any) -> bool:
    normalized = str(event_type or "").strip().lower()
    return normalized in {
        "chat.create",
        "turn.start",
        "turn.end",
        "message.final",
        "swarm.run.start",
        "proof.run.start",
    }


def _build_since_last_wake_summary(recent_timeline_events: list[dict[str, Any]]) -> dict[str, Any]:
    events = [row for row in recent_timeline_events if isinstance(row, dict)]
    if not events:
        return {
            "anchor": None,
            "summary": "No recent activity.",
            "counts": {"events": 0, "turns": 0, "approvals": 0, "notifications": 0, "decisions": 0, "provenance": 0},
            "timeline": [],
        }

    anchor_candidates = [row for row in events if _is_wake_anchor_event(row.get("event_type"))]
    anchor = min(anchor_candidates, key=lambda row: _sort_timestamp(row.get("timestamp"))) if anchor_candidates else events[-1]
    anchor_ts = anchor.get("timestamp")
    anchor_sort = _sort_timestamp(anchor_ts)
    since_events = [row for row in events if _sort_timestamp(row.get("timestamp")) >= anchor_sort]
    counts = {"events": len(since_events), "turns": 0, "approvals": 0, "notifications": 0, "decisions": 0, "provenance": 0}
    for row in since_events:
        event_type = str(row.get("event_type") or "").strip().lower()
        if event_type in {"turn.start", "turn.end", "message.final"}:
            counts["turns"] += 1
        elif event_type.startswith("approval."):
            counts["approvals"] += 1
        elif event_type == "notification":
            counts["notifications"] += 1
        elif event_type == "decision":
            counts["decisions"] += 1
        elif event_type == "provenance":
            counts["provenance"] += 1

    anchor_title = _normalize_text(anchor.get("title")) or "latest wake"
    anchor_detail = _normalize_text(anchor.get("detail"))
    summary = f"{counts['events']} events since {anchor_title}"
    if anchor_detail:
        summary = f"{summary} · {anchor_detail}"

    return {
        "anchor": {
            "event_id": anchor.get("event_id"),
            "timestamp": anchor_ts,
            "title": anchor_title,
            "detail": anchor_detail,
            "event_type": anchor.get("event_type"),
        },
        "summary": summary,
        "counts": counts,
        "timeline": since_events[:12],
    }


def build_activity_projection(
    *,
    recent_runs: list[dict[str, Any]] | None = None,
    recent_decisions: list[dict[str, Any]] | None = None,
    recent_support_claims: list[dict[str, Any]] | None = None,
    recent_notifications: list[dict[str, Any]] | None = None,
    recent_timeline_events: list[dict[str, Any]] | None = None,
    recent_provenance: list[dict[str, Any]] | None = None,
    view: str = "compact",
) -> dict[str, Any]:
    recent_runs = recent_runs if isinstance(recent_runs, list) else []
    recent_decisions = recent_decisions if isinstance(recent_decisions, list) else []
    recent_support_claims = recent_support_claims if isinstance(recent_support_claims, list) else []
    recent_notifications = recent_notifications if isinstance(recent_notifications, list) else []
    recent_timeline_events = recent_timeline_events if isinstance(recent_timeline_events, list) else []
    recent_provenance = recent_provenance if isinstance(recent_provenance, list) else []

    evidence_timeline = build_evidence_timeline_summary(
        recent_runs=recent_runs,
        recent_decisions=recent_decisions,
        recent_support_claims=recent_support_claims,
        recent_notifications=recent_notifications,
        recent_provenance=recent_provenance,
        recent_timeline_events=recent_timeline_events,
    )
    since_last_wake = _build_since_last_wake_summary(recent_timeline_events)
    compact = {
        "mode": "compact",
        "status": evidence_timeline.get("status"),
        "counts": evidence_timeline.get("counts") or {},
        "latest": evidence_timeline.get("latest"),
        "since_last_wake": since_last_wake,
    }
    expanded = {
        "mode": "expanded",
        "status": evidence_timeline.get("status"),
        "counts": evidence_timeline.get("counts") or {},
        "latest": evidence_timeline.get("latest"),
        "timeline": evidence_timeline.get("timeline") or [],
        "support_claims": evidence_timeline.get("support_claims") or [],
        "continuity_events": evidence_timeline.get("continuity_events") or [],
        "approval_events": evidence_timeline.get("approval_events") or [],
        "provenance_events": evidence_timeline.get("provenance_events") or [],
        "since_last_wake": since_last_wake,
    }
    active = compact if str(view or "compact").strip().lower() != "expanded" else expanded
    return {
        "view": "expanded" if active is expanded else "compact",
        "compact": compact,
        "expanded": expanded,
        "active": active,
        "since_last_wake": since_last_wake,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _sort_timestamp(value: Any) -> float:
    if not value:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def get_recent_activity(
    limit_runs: int = 10,
    limit_decisions: int = 20,
    *,
    entity_id: str | None = None,
    chat_id: str | None = None,
    run_id: str | None = None,
    workflow_id: str | None = None,
    projection_view: str = "compact",
) -> dict[str, Any]:
    """Combined recent runs, decisions, and overseer summary."""
    recent_runs = get_recent_runs(limit_runs)
    recent_decisions = get_recent_decisions(limit_decisions)
    recent_notifications = get_recent_human_notifications(limit_decisions)
    recent_support_claims = get_recent_support_claims(limit_decisions)
    recent_timeline_events = get_recent_timeline_events(
        limit=max(limit_runs, limit_decisions),
        entity_id=entity_id,
        chat_id=chat_id,
        run_id=run_id,
        workflow_id=workflow_id,
    )
    recent_provenance = [item for item in recent_timeline_events if item.get("provenance_href")]
    return {
        "recent_runs": recent_runs,
        "recent_decisions": recent_decisions,
        "recent_notifications": recent_notifications,
        "recent_support_claims": recent_support_claims,
        "recent_timeline_events": recent_timeline_events,
        "activity_projection": build_activity_projection(
            recent_runs=recent_runs,
            recent_decisions=recent_decisions,
            recent_support_claims=recent_support_claims,
            recent_notifications=recent_notifications,
            recent_timeline_events=recent_timeline_events,
            recent_provenance=recent_provenance,
            view=projection_view,
        ),
        "evidence_timeline": build_evidence_timeline_summary(
            recent_runs=recent_runs,
            recent_decisions=recent_decisions,
            recent_support_claims=recent_support_claims,
            recent_notifications=recent_notifications,
            recent_provenance=recent_provenance,
            recent_timeline_events=recent_timeline_events,
        ),
        "overseer": get_overseer_summary(),
    }
