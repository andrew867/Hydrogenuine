"""DB-backed access log for co-access (molecules).

The gateway database is the source of truth. The old JSONL file path is retired.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from hg_gateway.db import get_connection

try:
    from hg_lib.config import get_workspace_root
except ImportError:
    def get_workspace_root() -> Path:
        return Path(os.getcwd())


SCHEMA_VERSION = 1
EVENT_TYPE = "access_log"


def canonicalize_subject(subject_type: str, subject: str) -> str:
    """
    Normalize subject for storage and grouping (e.g. path separators, case).
    subject_type: "path" | "entity_id" | "url" | "other"
    subject: raw subject string
    """
    if not subject or not isinstance(subject, str):
        return ""
    s = subject.strip()
    if subject_type == "path":
        s = s.replace("\\", "/").strip()
        if s.startswith("./"):
            s = s[2:]
        return s
    if subject_type in ("entity_id", "url", "other"):
        return s
    return s


def _db_path(workspace_root: Optional[Path] = None) -> str | None:
    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    root = workspace_root if workspace_root is not None else get_workspace_root()
    try:
        return str((Path(root) / "memory" / "gateway.sqlite3").resolve())
    except Exception:
        return None


def _insert_event(
    *,
    workspace_root: Optional[Path],
    payload: dict[str, Any],
) -> None:
    db_path = _db_path(workspace_root)
    if not db_path:
        return
    tenant_id = str(payload.get("scope_id") or "default")
    created_at = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
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
                    json.dumps(payload, ensure_ascii=False),
                    created_at,
                ),
            )
    except Exception:
        pass


def log_access(
    agent_id: str,
    access_type: str,
    subject_type: str,
    subject: str,
    source: str,
    tags: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> None:
    """
    Log a single access event (atom). Best-effort; never raises.

    The event is persisted to the gateway DB audit ledger.
    """
    try:
        scope = {}
        try:
            from hg_core.scope_context import get_scope
            scope = get_scope()
        except Exception:
            pass
        effective_agent_id = agent_id or scope.get("session_id", "").replace("automation-", "", 1) or ""
        subject_canon = canonicalize_subject(subject_type, subject)
        event = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": effective_agent_id,
            "access_type": access_type,
            "subject_type": subject_type,
            "subject": subject_canon,
            "source": source,
        }
        if scope:
            event["scope_type"] = scope.get("scope_type", "")
            event["scope_id"] = scope.get("scope_id", "")
            if scope.get("run_id"):
                event["run_id"] = scope["run_id"]
            if scope.get("session_id"):
                event["session_id"] = scope["session_id"]
            if scope.get("cycle_id"):
                event["cycle_id"] = scope["cycle_id"]
        if tags:
            event["tags"] = tags
        if extra:
            event["extra"] = extra
        _insert_event(workspace_root=workspace_root, payload=event)

        # Sticky Reality ledger: emit READ/WRITE for co-access materializer.
        if access_type in ("read", "write"):
            root = workspace_root if workspace_root is not None else get_workspace_root()
            try:
                from hg_core.ledger import emit
                led_scope = {"type": scope.get("scope_type", "global"), "id": scope.get("scope_id", "default")} if scope else {"type": "global", "id": "default"}
                emit(
                    "READ" if access_type == "read" else "WRITE",
                    subject_type if subject_type in ("entity", "path", "url", "other") else "entity",
                    subject_canon or "unknown",
                    {"reason": source, "agent_id": effective_agent_id},
                    scope=led_scope,
                    workspace_root=root,
                )
            except Exception:
                pass
    except Exception:
        pass


def iter_access_events(
    agent_id: Optional[str] = None,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    source: Optional[str] = None,
    limit: Optional[int] = None,
    workspace_root: Optional[Path] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Iterate access log events from the gateway DB.
    """
    db_path = _db_path(workspace_root)
    if not db_path:
        return
    count = 0
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload, created_at
                FROM audit_events
                WHERE event_type = ?
                ORDER BY created_at ASC, event_id ASC
                """,
                (EVENT_TYPE,),
            ).fetchall()
    except Exception:
        return

    for row in rows:
        payload_raw = row[0] if not isinstance(row, dict) else row.get("payload")
        try:
            event = json.loads(payload_raw) if payload_raw else {}
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        if agent_id is not None and event.get("agent_id") != agent_id:
            continue
        if scope_type is not None and event.get("scope_type") != scope_type:
            continue
        if scope_id is not None and event.get("scope_id") != scope_id:
            continue
        if source is not None and event.get("source") != source:
            continue
        count += 1
        if limit is not None and count > limit:
            return
        yield event


def get_molecule_from_access_log(
    scope_type: str,
    scope_id: str,
    agent_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Derive molecule (what was read together) from access log for a given scope.
    Returns: subjects (unique list), counts (per subject), sources (list).
    """
    subjects: List[str] = []
    counts: Dict[str, int] = {}
    sources: List[str] = []
    for event in iter_access_events(
        agent_id=agent_id,
        scope_type=scope_type,
        scope_id=scope_id,
        workspace_root=workspace_root,
    ):
        sub = event.get("subject")
        if sub:
            subjects.append(sub)
            counts[sub] = counts.get(sub, 0) + 1
        src = event.get("source")
        if src:
            sources.append(src)
    return {
        "subjects": list(dict.fromkeys(subjects)),
        "counts": counts,
        "sources": sources,
    }


def get_co_occurrence(
    subject: str,
    top_k: int = 20,
    scope_type: Optional[str] = None,
    agent_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> List[tuple]:
    """
    Compute co-occurrence: for each scope that contains subject, count other subjects.
    """
    from collections import Counter

    scope_subjects: Dict[str, set] = {}
    try:
        for event in iter_access_events(
            agent_id=agent_id,
            scope_type=scope_type,
            workspace_root=workspace_root,
        ):
            if event.get("access_type") != "read":
                continue
            sc_type = event.get("scope_type")
            sc_id = event.get("scope_id")
            if not sc_type or not sc_id:
                continue
            key = f"{sc_type}:{sc_id}"
            sub = event.get("subject")
            if sub:
                scope_subjects.setdefault(key, set()).add(sub)
    except Exception:
        return []

    other_counts: Counter = Counter()
    for subs in scope_subjects.values():
        if subject not in subs:
            continue
        for s in subs:
            if s != subject:
                other_counts[s] += 1
    return other_counts.most_common(top_k)
