from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.human_notifications import list_human_notifications
from hg_core.browser.session_health import evaluate_browser_session_health
from hg_gateway.db import _get_db_path, get_connection


def safe_json_load(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        p = Path(path)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _activity_age_bucket(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return None
    delta = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
    if delta.total_seconds() < 6 * 3600:
        return "fresh"
    if delta.total_seconds() < 24 * 3600:
        return "recent"
    if delta.total_seconds() < 72 * 3600:
        return "stale"
    return "old"


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def artifacts_for_related(related_kind: str, related_id: str) -> list[dict[str, Any]]:
    try:
        with get_connection(_get_db_path()) as conn:
            rows = conn.execute(
                """SELECT proof_id, artifact_type, path, metadata_json, created_at
                   FROM proof_artifacts
                   WHERE related_kind = ? AND related_id = ?
                   ORDER BY created_at DESC, proof_id DESC""",
                (related_kind, related_id),
            ).fetchall()
    except Exception:
        return []
    items = []
    for row in rows:
        try:
            metadata = json.loads(row[3]) if row[3] else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        items.append(
            {
                "proof_id": row[0],
                "artifact_type": row[1],
                "path": row[2],
                "metadata": metadata,
                "created_at": row[4],
            }
        )
    return items


def session_by_id(session_id: str, tenant_id: str) -> dict[str, Any] | None:
    try:
        with get_connection(_get_db_path()) as conn:
            row = conn.execute(
                """SELECT browser_session_id, tenant_id, entity_id, platform, state, started_at, ended_at, trace_path, latest_screenshot_path
                   FROM browser_sessions
                   WHERE browser_session_id = ? AND tenant_id = ?""",
                (session_id, tenant_id),
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "browser_session_id": row[0],
        "tenant_id": row[1],
        "entity_id": row[2],
        "platform": row[3],
        "state": row[4],
        "started_at": row[5],
        "ended_at": row[6],
        "trace_path": row[7],
        "latest_screenshot_path": row[8],
    }


def latest_social_account_proof_summary(social_account_id: str) -> dict[str, Any] | None:
    rows = [
        item
        for item in artifacts_for_related("social_account", social_account_id)
        if str(item.get("artifact_type") or "").strip().lower() != "browser_session_binding"
    ]
    if not rows:
        return {
            "artifact_count": 0,
            "latest_artifact_type": None,
            "latest_created_at": None,
            "latest_handle": None,
            "latest_url": None,
            "latest_state": None,
        }
    latest = rows[0]
    payload = safe_json_load(latest.get("path"))
    metadata = latest.get("metadata") if isinstance(latest.get("metadata"), dict) else {}
    return {
        "artifact_count": len(rows),
        "latest_artifact_type": latest.get("artifact_type"),
        "latest_created_at": latest.get("created_at"),
        "latest_handle": (payload or {}).get("handle") or metadata.get("handle"),
        "latest_url": (payload or {}).get("url") or metadata.get("url"),
        "latest_state": (payload or {}).get("state"),
    }


def latest_social_account_continuity_summary(social_account_id: str) -> dict[str, Any] | None:
    account_artifacts = artifacts_for_related("social_account", social_account_id)
    bindings: list[dict[str, Any]] = []
    for artifact in account_artifacts:
        if artifact.get("artifact_type") != "browser_session_binding":
            continue
        payload = safe_json_load(artifact.get("path")) or {}
        session_id = str(payload.get("browser_session_id") or payload.get("session_id") or "").strip()
        tenant_id = str(payload.get("tenant_id") or "default").strip() or "default"
        session = session_by_id(session_id, tenant_id) if session_id else None
        session_artifacts = artifacts_for_related("browser_session", session_id) if session_id else []
        health = evaluate_browser_session_health(session, session_artifacts) if session else None
        degraded_artifact = next((item for item in session_artifacts if item.get("artifact_type") == "session_degraded"), None)
        status = "healthy"
        if health and health.get("status") == "degraded":
            status = "degraded"
        elif session and str(session.get("state") or "").strip().lower() == "degraded":
            status = "degraded"
        elif not session:
            status = "missing"
        bindings.append(
            {
                "binding": artifact,
                "payload": payload,
                "session": session,
                "health": health,
                "status": status,
                "degraded_artifact": degraded_artifact,
                "binding_created_at": _parse_timestamp(artifact.get("created_at")),
                "session_started_at": _parse_timestamp(session.get("started_at") if session else None),
            }
        )

    if not bindings:
        return {
            "status": "unbound",
            "browser_session_id": None,
            "health": None,
            "degraded_at": None,
            "degraded_reason": None,
        }

    selected = max(
        bindings,
        key=lambda item: (
            1 if item.get("status") == "healthy" else 0,
            1 if item.get("session") else 0,
            item.get("session_started_at") or datetime.min.replace(tzinfo=timezone.utc),
            item.get("binding_created_at") or datetime.min.replace(tzinfo=timezone.utc),
        ),
    )
    session = selected.get("session")
    health = selected.get("health")
    status = str(selected.get("status") or "missing")
    degraded_artifact = selected.get("degraded_artifact") if isinstance(selected.get("degraded_artifact"), dict) else None
    payload = selected.get("payload") if isinstance(selected.get("payload"), dict) else {}
    return {
        "status": status,
        "browser_session_id": payload.get("browser_session_id"),
        "browser_session_started_at": session.get("started_at") if session else None,
        "health": health,
        "degraded_at": degraded_artifact.get("created_at") if degraded_artifact else None,
        "degraded_reason": degraded_artifact.get("path") if degraded_artifact else None,
    }


def _bound_browser_session_ids(account_artifacts: list[dict[str, Any]]) -> list[str]:
    session_ids: list[str] = []
    for artifact in account_artifacts:
        if artifact.get("artifact_type") != "browser_session_binding":
            continue
        payload = safe_json_load(artifact.get("path"))
        session_id = str((payload or {}).get("browser_session_id") or (payload or {}).get("session_id") or "").strip()
        if session_id and session_id not in session_ids:
            session_ids.append(session_id)
    return session_ids


def social_account_continuity_injury_summary(
    social_account_id: str,
    continuity_summary: dict[str, Any] | None,
    notification_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    continuity_summary = continuity_summary if isinstance(continuity_summary, dict) else {}
    notification_summary = notification_summary if isinstance(notification_summary, dict) else {}
    continuity_status = str(continuity_summary.get("status") or "").strip().lower()
    degraded_at = _parse_timestamp(continuity_summary.get("degraded_at"))
    degraded_reason = continuity_summary.get("degraded_reason")
    account_artifacts = artifacts_for_related("social_account", social_account_id)
    for session_id in _bound_browser_session_ids(account_artifacts):
        for artifact in artifacts_for_related("browser_session", session_id):
            if artifact.get("artifact_type") != "session_degraded":
                continue
            candidate_at = _parse_timestamp(artifact.get("created_at"))
            if candidate_at is None:
                continue
            if degraded_at is None or candidate_at > degraded_at:
                degraded_at = candidate_at
                degraded_reason = artifact.get("path")
    started_at = _parse_timestamp(continuity_summary.get("browser_session_started_at"))

    latest_notification = notification_summary.get("latest") if isinstance(notification_summary.get("latest"), dict) else {}
    latest_notification_at = _parse_timestamp(latest_notification.get("timestamp"))
    latest_notification_kind = str(latest_notification.get("kind") or "").strip() or None
    latest_notification_message = str(latest_notification.get("message") or "").strip() or None

    status = "none"
    active = False
    repaired = False
    if degraded_at is not None:
        if continuity_status in {"degraded", "missing"}:
            status = "active"
            active = True
        else:
            status = "recovered"
            repaired = True
    elif continuity_status in {"degraded", "missing"}:
        status = "active"
        active = True

    repair_at = None
    repair_kind = None
    repair_detail = None
    if repaired:
        if started_at is not None and (degraded_at is None or started_at >= degraded_at):
            repair_at = _isoformat_utc(started_at)
            repair_kind = "session_restart"
            repair_detail = continuity_summary.get("browser_session_id")
        elif latest_notification_at is not None and (degraded_at is None or latest_notification_at >= degraded_at):
            repair_at = _isoformat_utc(latest_notification_at)
            repair_kind = latest_notification_kind
            repair_detail = latest_notification_message

    return {
        "status": status,
        "active": active,
        "repaired": repaired,
        "last_injury_at": _isoformat_utc(degraded_at),
        "last_injury_reason": degraded_reason,
        "last_repair_at": repair_at,
        "last_repair_kind": repair_kind,
        "last_repair_detail": repair_detail,
    }


def social_account_readiness_summary(account: dict[str, Any], continuity_summary: dict[str, Any] | None, proof_summary: dict[str, Any] | None) -> dict[str, Any]:
    account_state = str(account.get("state") or "").strip().lower()
    continuity_status = str((continuity_summary or {}).get("status") or "").strip().lower()
    checks = {
        "account_usable_state": account_state in {"active", "verified", "pending"},
        "login_binding_present": bool(account.get("login_secret_alias_id")),
        "browser_session_present": bool((continuity_summary or {}).get("browser_session_id")),
        "continuity_healthy": continuity_status != "degraded",
        "proof_present": bool((proof_summary or {}).get("artifact_count")),
    }
    blocking = [name for name, ok in checks.items() if not ok and name != "browser_session_present"]
    return {
        "ready": not blocking,
        "checks": checks,
        "blocking": blocking,
        "summary": {
            "state": account_state or None,
            "browser_session_id": (continuity_summary or {}).get("browser_session_id"),
            "continuity_status": continuity_status or None,
        },
    }


def recent_social_account_notification_summary(account: dict[str, Any], limit: int = 3) -> dict[str, Any]:
    root = _workspace_root()
    if root is None:
        return {"count": 0, "items": [], "latest": None}
    platform = str(account.get("platform") or "").strip().lower()
    social_account_id = str(account.get("social_account_id") or "").strip()
    matches: list[dict[str, Any]] = []
    for row in list_human_notifications(root, limit=max(50, limit * 5)):
        if not isinstance(row, dict):
            continue
        notification_social_account_id = str(row.get("social_account_id") or "").strip()
        if social_account_id and notification_social_account_id:
            if notification_social_account_id != social_account_id:
                continue
        else:
            summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
            execution = summary.get("execution") if isinstance(summary, dict) else {}
            execution = execution if isinstance(execution, dict) else {}
            notification_platform = str(execution.get("platform") or "").strip().lower()
            task_name = str(row.get("task_name") or "").strip().lower()
            if platform and notification_platform != platform and platform not in task_name:
                continue
        matches.append(
            {
                "timestamp": row.get("timestamp"),
                "task_name": row.get("task_name"),
                "kind": row.get("kind"),
                "message": row.get("message"),
                "transport": row.get("transport"),
            }
        )
        if len(matches) >= max(1, limit):
            break
    matches.sort(
        key=lambda item: (
            _parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
            str(item.get("task_name") or ""),
            str(item.get("kind") or ""),
        ),
        reverse=True,
    )
    limited = matches[: max(1, limit)]
    return {
        "count": len(limited),
        "items": limited,
        "latest": limited[0] if limited else None,
    }


def social_account_last_activity_summary(
    proof_summary: dict[str, Any] | None,
    continuity_summary: dict[str, Any] | None,
    notification_summary: dict[str, Any] | None,
    continuity_injury_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kind_priority = {"proof": 0, "notification": 1, "continuity_issue": 2}
    candidates: list[tuple[datetime, str, str | None]] = []

    proof_at = _parse_timestamp((proof_summary or {}).get("latest_created_at"))
    if proof_at is not None:
        candidates.append((proof_at, "proof", (proof_summary or {}).get("latest_artifact_type")))

    notification_latest = (notification_summary or {}).get("latest") if isinstance(notification_summary, dict) else None
    notification_at = _parse_timestamp((notification_latest or {}).get("timestamp"))
    if notification_at is not None:
        candidates.append((notification_at, "notification", (notification_latest or {}).get("kind")))

    continuity_issue_at = _parse_timestamp((continuity_injury_summary or {}).get("last_injury_at")) or _parse_timestamp((continuity_summary or {}).get("degraded_at"))
    continuity_issue_detail = (continuity_injury_summary or {}).get("last_injury_reason") or (continuity_summary or {}).get("degraded_reason")
    if continuity_issue_at is not None:
        candidates.append((continuity_issue_at, "continuity_issue", continuity_issue_detail))

    if not candidates:
        return {
            "last_seen_at": None,
            "last_seen_kind": None,
            "last_seen_detail": None,
            "age_bucket": None,
            "stale": None,
        }

    last_seen_at, last_seen_kind, last_seen_detail = max(
        candidates,
        key=lambda item: (item[0], kind_priority.get(item[1], 0)),
    )
    age_bucket = _activity_age_bucket(last_seen_at)
    return {
        "last_seen_at": _isoformat_utc(last_seen_at),
        "last_seen_kind": last_seen_kind,
        "last_seen_detail": last_seen_detail,
        "age_bucket": age_bucket,
        "stale": age_bucket in {"stale", "old"},
    }


def build_social_account_operator_summary(social_account_id: str, account: dict[str, Any] | None = None) -> dict[str, Any]:
    account_payload = account or {}
    proof_summary = latest_social_account_proof_summary(social_account_id)
    continuity_summary = latest_social_account_continuity_summary(social_account_id)
    notification_summary = recent_social_account_notification_summary(account_payload)
    continuity_injury_summary = social_account_continuity_injury_summary(social_account_id, continuity_summary, notification_summary)
    return {
        "proof_summary": proof_summary,
        "continuity_summary": continuity_summary,
        "readiness_summary": social_account_readiness_summary(account_payload, continuity_summary, proof_summary),
        "notification_summary": notification_summary,
        "continuity_injury_summary": continuity_injury_summary,
        "last_activity_summary": social_account_last_activity_summary(proof_summary, continuity_summary, notification_summary, continuity_injury_summary),
    }
