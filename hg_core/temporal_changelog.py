from __future__ import annotations

"""DB-backed temporal changelog for continuity / disruption events."""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from hg_gateway.db import get_connection

ENTITY_VISIBLE_KINDS = {"outage", "time_jump", "migration"}
ENTITY_VISIBLE_SEVERITIES = {"high", "critical"}
EVENT_TYPE = "temporal_changelog"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _workspace_root(workspace_root: Path | None = None) -> Path:
    if workspace_root is not None:
        return Path(workspace_root)
    from hg_lib.config import get_workspace_root

    return get_workspace_root()


def _db_path(workspace_root: Path | None = None) -> str | None:
    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    root = _workspace_root(workspace_root)
    try:
        return str((root / "memory" / "gateway.sqlite3").resolve())
    except Exception:
        return None


def _normalize_event(payload: dict[str, Any]) -> dict[str, Any]:
    event = dict(payload)
    event.setdefault("event_id", uuid.uuid4().hex[:16])
    event.setdefault("recorded_at", _iso_now())
    event.setdefault("kind", "platform")
    event.setdefault("severity", "info")
    event.setdefault("tags", [])
    event.setdefault("affected_entities", [])
    return event


def _insert_event(*, workspace_root: Path | None, payload: dict[str, Any]) -> None:
    db_path = _db_path(workspace_root)
    if not db_path:
        return
    tenant_id = "default"
    created_at = str(payload.get("recorded_at") or _iso_now())
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_events (tenant_id, event_type, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    EVENT_TYPE,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    created_at,
                ),
            )
    except Exception:
        pass


def record_temporal_event(
    *,
    title: str,
    summary: str,
    workspace_root: Path | None = None,
    kind: str = "platform",
    severity: str = "info",
    start_at: str | None = None,
    end_at: str | None = None,
    tags: Optional[Iterable[str]] = None,
    affected_entities: Optional[Iterable[str]] = None,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    event = _normalize_event(
        {
            "title": title,
            "summary": summary,
            "kind": kind,
            "severity": severity,
            "start_at": start_at or _iso_now(),
            "end_at": end_at,
            "tags": list(tags or []),
            "affected_entities": list(affected_entities or []),
            "details": details or {},
        }
    )
    _insert_event(workspace_root=workspace_root, payload=event)
    return event


def _event_when(event: dict[str, Any]) -> datetime | None:
    when = str(event.get("end_at") or event.get("start_at") or event.get("recorded_at") or "")
    try:
        return datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError:
        return None


def record_major_disruption_once(
    *,
    title: str,
    summary: str,
    workspace_root: Path | None = None,
    dedupe_key: str,
    kind: str,
    start_at: str | None = None,
    end_at: str | None = None,
    severity: str = "high",
    tags: Optional[Iterable[str]] = None,
    affected_entities: Optional[Iterable[str]] = None,
    details: Optional[dict[str, Any]] = None,
    within_hours: int = 12,
) -> dict[str, Any] | None:
    recent = load_recent_temporal_events(
        workspace_root=workspace_root,
        agent_id=None,
        limit=100,
        days=max(1, within_hours // 24 + 2),
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, within_hours))
    for event in recent:
        event_key = str((event.get("details") or {}).get("dedupe_key") or "")
        if event_key != dedupe_key:
            continue
        when = _event_when(event)
        if when is not None and when >= cutoff:
            return None
    payload_details = dict(details or {})
    payload_details["dedupe_key"] = dedupe_key
    return record_temporal_event(
        title=title,
        summary=summary,
        workspace_root=workspace_root,
        kind=kind,
        severity=severity,
        start_at=start_at,
        end_at=end_at,
        tags=tags,
        affected_entities=affected_entities,
        details=payload_details,
    )


def load_recent_temporal_events(
    *,
    workspace_root: Path | None = None,
    agent_id: str | None = None,
    limit: int = 5,
    days: int = 30,
) -> list[dict[str, Any]]:
    db_path = _db_path(workspace_root)
    if not db_path:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    rows: list[dict[str, Any]] = []
    try:
        with get_connection(db_path) as conn:
            records = conn.execute(
                """
                SELECT payload, created_at
                FROM audit_events
                WHERE event_type = ?
                ORDER BY created_at ASC, event_id ASC
                """,
                (EVENT_TYPE,),
            ).fetchall()
    except Exception:
        return []
    for row in records:
        payload_raw = row[0] if not isinstance(row, dict) else row.get("payload")
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        event = _normalize_event(payload)
        when = str(event.get("end_at") or event.get("start_at") or event.get("recorded_at") or "")
        try:
            dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            dt = None
        if dt is not None and dt < cutoff:
            continue
        affected = [str(item) for item in event.get("affected_entities", []) if str(item).strip()]
        if agent_id and affected and agent_id not in affected and "all" not in affected:
            continue
        kind = str(event.get("kind") or "").strip().lower()
        severity = str(event.get("severity") or "").strip().lower()
        if kind not in ENTITY_VISIBLE_KINDS:
            continue
        if severity not in ENTITY_VISIBLE_SEVERITIES:
            continue
        rows.append(event)
    rows.sort(key=lambda item: str(item.get("end_at") or item.get("start_at") or item.get("recorded_at") or ""), reverse=True)
    return rows[: max(1, limit)]


def format_temporal_events(events: list[dict[str, Any]], *, max_items: int = 3) -> list[str]:
    lines: list[str] = []
    for event in events[: max(1, max_items)]:
        when = str(event.get("end_at") or event.get("start_at") or event.get("recorded_at") or "")[:10]
        title = str(event.get("title") or "System update").strip()
        summary = str(event.get("summary") or "").strip()
        line = f"{when}: {title}"
        if summary:
            line += f" - {summary}"
        lines.append(line[:220].rstrip())
    return lines
