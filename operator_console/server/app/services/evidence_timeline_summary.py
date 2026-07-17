from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _sort_timestamp(value: Any) -> float:
    parsed = _parse_timestamp(value)
    if not parsed:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _timeline_entry(kind: str, timestamp: Any, title: str, detail: str | None = None, href: str | None = None) -> dict[str, Any]:
    return {
        "kind": kind,
        "timestamp": timestamp,
        "title": title,
        "detail": detail,
        "href": href,
    }


def build_evidence_timeline_summary(
    *,
    recent_runs: list[dict[str, Any]] | None = None,
    recent_decisions: list[dict[str, Any]] | None = None,
    recent_support_claims: list[dict[str, Any]] | None = None,
    recent_notifications: list[dict[str, Any]] | None = None,
    recent_provenance: list[dict[str, Any]] | None = None,
    recent_timeline_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    recent_runs = recent_runs if isinstance(recent_runs, list) else []
    recent_decisions = recent_decisions if isinstance(recent_decisions, list) else []
    recent_support_claims = recent_support_claims if isinstance(recent_support_claims, list) else []
    recent_notifications = recent_notifications if isinstance(recent_notifications, list) else []
    recent_provenance = recent_provenance if isinstance(recent_provenance, list) else []
    recent_timeline_events = recent_timeline_events if isinstance(recent_timeline_events, list) else []

    timeline: list[dict[str, Any]] = []
    support_claims: list[dict[str, Any]] = []
    continuity_events: list[dict[str, Any]] = []
    approval_events: list[dict[str, Any]] = []
    provenance_events: list[dict[str, Any]] = []
    reflection_events: list[dict[str, Any]] = []
    drift_events: list[dict[str, Any]] = []

    for row in recent_runs:
        if not isinstance(row, dict):
            continue
        status = _normalize_text(row.get("status")) or "unknown"
        started_at = row.get("started_at")
        timeline.append(_timeline_entry("run", started_at, f"Run {status}", _normalize_text(row.get("graph_id")) or _normalize_text(row.get("run_id"))))

    support_source = recent_support_claims if recent_support_claims else recent_decisions
    for row in support_source:
        if not isinstance(row, dict):
            continue
        timestamp = row.get("timestamp")
        action = _normalize_text(row.get("action") or row.get("decision")) or "decision"
        rationale = _normalize_text(row.get("rationale") or row.get("decision_note"))
        outcome = _normalize_text(row.get("outcome") or row.get("decision"))
        support_claims.append(
            {
                "timestamp": timestamp,
                "decision_id": row.get("decision_id") or row.get("approval_id") or row.get("ledger_id"),
                "approval_id": row.get("approval_id"),
                "action": action,
                "rationale": rationale,
                "outcome": outcome,
            }
        )
        timeline.append(_timeline_entry("decision", timestamp, action, rationale or outcome))

    continuity_kinds = {
        "continuity_recovery_ack",
        "continuity_runtime_observed",
        "post_rebuild_continuity_required",
        "post_rebuild_continuity_verified",
        "post_rebuild_runtime_observed",
        "identity_restore_runtime_observed",
        "supervised_resume_runtime_observed",
        "identity_resume_closeout",
        "operational_resume_checkpoint",
        "operational_resume_checkpoint_invalidated",
    }
    for row in recent_notifications:
        if not isinstance(row, dict):
            continue
        timestamp = row.get("timestamp")
        kind = _normalize_text(row.get("kind")) or "notification"
        governance_label = _normalize_text(row.get("governance_label")) or kind
        governance_detail = _normalize_text(row.get("governance_detail"))
        approval_href = _normalize_text(row.get("approval_href"))
        review_release_state = row.get("review_release_state") if isinstance(row.get("review_release_state"), dict) else {}
        if kind in continuity_kinds or "continuity" in kind or "rebuild" in kind or "resume" in kind:
            continuity_events.append(
                {
                    "timestamp": timestamp,
                    "kind": kind,
                    "message": _normalize_text(row.get("message")),
                    "governance_label": governance_label,
                    "governance_detail": governance_detail,
                    "approval_href": approval_href,
                }
            )
        if approval_href or review_release_state:
            approval_events.append(
                {
                    "timestamp": timestamp,
                    "kind": kind,
                    "message": _normalize_text(row.get("message")),
                    "governance_label": governance_label,
                    "governance_detail": governance_detail,
                    "approval_href": approval_href,
                    "review_release_state": review_release_state,
                }
            )
        timeline.append(_timeline_entry("notification", timestamp, governance_label, governance_detail or _normalize_text(row.get("message")), approval_href))

    for row in recent_provenance:
        if not isinstance(row, dict):
            continue
        timestamp = row.get("timestamp")
        title = _normalize_text(row.get("title")) or "Why this reply"
        detail = _normalize_text(row.get("detail"))
        href = _normalize_text(row.get("provenance_href"))
        provenance_events.append(
            {
                "timestamp": timestamp,
                "event_id": row.get("event_id"),
                "chat_id": row.get("chat_id"),
                "message_id": row.get("message_id"),
                "title": title,
                "detail": detail,
                "provenance_href": href,
            }
        )
        timeline.append(_timeline_entry("provenance", timestamp, title, detail, href))

    for row in recent_timeline_events:
        if not isinstance(row, dict):
            continue
        event_type = _normalize_text(row.get("event_type")) or ""
        if not event_type.startswith("reflection.artifact.") and event_type != "drift.detected":
            continue
        timestamp = row.get("timestamp")
        title = _normalize_text(row.get("title")) or ("Drift detected" if event_type == "drift.detected" else "Reflection event")
        detail = _normalize_text(row.get("detail"))
        href = _normalize_text(row.get("href"))
        if event_type == "drift.detected":
            drift_events.append(
                {
                    "timestamp": timestamp,
                    "event_id": row.get("event_id"),
                    "event_type": event_type,
                    "title": title,
                    "detail": detail,
                    "href": href,
                    "severity": _normalize_text(row.get("severity")),
                    "summary": _normalize_text(row.get("summary")),
                }
            )
            timeline.append(_timeline_entry("drift", timestamp, title, detail, href))
        else:
            reflection_events.append(
                {
                    "timestamp": timestamp,
                    "event_id": row.get("event_id"),
                    "event_type": event_type,
                    "title": title,
                    "detail": detail,
                    "href": href,
                }
            )
            timeline.append(_timeline_entry("reflection", timestamp, title, detail, href))

    timeline.sort(key=lambda item: _sort_timestamp(item.get("timestamp")), reverse=True)
    support_claims.sort(key=lambda item: _sort_timestamp(item.get("timestamp")), reverse=True)
    continuity_events.sort(key=lambda item: _sort_timestamp(item.get("timestamp")), reverse=True)
    approval_events.sort(key=lambda item: _sort_timestamp(item.get("timestamp")), reverse=True)
    provenance_events.sort(key=lambda item: _sort_timestamp(item.get("timestamp")), reverse=True)
    reflection_events.sort(key=lambda item: _sort_timestamp(item.get("timestamp")), reverse=True)

    latest = timeline[0] if timeline else None
    counts = {
        "runs": len(recent_runs),
        "decisions": len(recent_decisions),
        "notifications": len(recent_notifications),
        "continuity_events": len(continuity_events),
        "approval_events": len(approval_events),
        "support_claims": len(support_claims),
        "provenance_events": len(provenance_events),
        "reflection_events": len(reflection_events),
        "drift_events": len(drift_events),
    }
    active_status = "healthy" if latest else "missing"
    if counts["continuity_events"] and counts["approval_events"]:
        active_status = "healthy"
    elif counts["continuity_events"] or counts["approval_events"] or counts["support_claims"]:
        active_status = "partial"

    evidence_total = counts["runs"] + counts["decisions"] + counts["notifications"] + counts["provenance_events"] + counts["reflection_events"]
    quality = {
        "coverage_score": round(min(1.0, (counts["continuity_events"] + counts["approval_events"] + counts["support_claims"]) / max(1, evidence_total)), 3),
        "attribution_score": round(min(1.0, (counts["provenance_events"] + counts["support_claims"] + counts["continuity_events"]) / max(1, evidence_total)), 3),
        "operator_override_rate": round(counts["approval_events"] / max(1, counts["continuity_events"] + counts["approval_events"]), 3),
        "promotion_accuracy": round(counts["support_claims"] / max(1, counts["support_claims"] + counts["approval_events"]), 3),
        "status": "healthy" if counts["continuity_events"] and counts["approval_events"] else ("partial" if counts["support_claims"] or counts["provenance_events"] else "missing"),
    }

    return {
        "status": active_status,
        "counts": counts,
        "latest": latest,
        "timeline": timeline[:24],
        "support_claims": support_claims[:12],
        "continuity_events": continuity_events[:12],
        "approval_events": approval_events[:12],
        "provenance_events": provenance_events[:12],
        "reflection_events": reflection_events[:12],
        "drift_events": drift_events[:12],
        "quality": quality,
    }
