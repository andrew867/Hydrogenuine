from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_gateway.db import _get_db_path, get_connection


def path_exists(path: Optional[str]) -> bool:
    if not path:
        return False
    try:
        return Path(path).exists()
    except OSError:
        return False


def evaluate_browser_session_health(
    session: Optional[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not session:
        return None
    profile_artifact = next((item for item in artifacts if item.get("artifact_type") == "profile_dir"), None)
    latest_snapshot = next((item for item in artifacts if item.get("artifact_type") == "snapshot"), None)
    latest_restore = next((item for item in artifacts if item.get("artifact_type") == "session_restore"), None)
    trace_path = session.get("trace_path")
    latest_screenshot_path = session.get("latest_screenshot_path")
    state = str(session.get("state") or "").strip().lower()
    issues: list[str] = []

    profile_dir = profile_artifact.get("path") if profile_artifact else None
    if state in {"active", "awaiting_human"} and not path_exists(profile_dir):
        issues.append("missing_profile_dir")
    if latest_screenshot_path and not path_exists(latest_screenshot_path):
        issues.append("missing_latest_screenshot")
    if trace_path and not path_exists(trace_path):
        issues.append("missing_trace")
    if latest_snapshot and not path_exists(latest_snapshot.get("path")):
        issues.append("missing_latest_snapshot")

    status = "healthy"
    if issues:
        status = "degraded"
    elif state == "closed":
        status = "closed"

    return {
        "status": status,
        "issues": issues,
        "profile_dir": profile_dir,
        "profile_dir_exists": path_exists(profile_dir),
        "latest_screenshot_path": latest_screenshot_path,
        "latest_screenshot_exists": path_exists(latest_screenshot_path),
        "trace_path": trace_path,
        "trace_exists": path_exists(trace_path),
        "latest_snapshot_path": latest_snapshot.get("path") if latest_snapshot else None,
        "latest_snapshot_exists": path_exists(latest_snapshot.get("path") if latest_snapshot else None),
        "latest_restore_at": latest_restore.get("created_at") if latest_restore else None,
    }


def browser_session_is_reusable(
    session: Optional[Dict[str, Any]],
    *,
    artifacts: List[Dict[str, Any]],
) -> bool:
    if not session:
        return False
    if str(session.get("state") or "").strip().lower() not in {"active", "awaiting_human"}:
        return False
    health = evaluate_browser_session_health(session, artifacts)
    return bool(health and health.get("status") != "degraded")


def mark_browser_session_degraded(
    session_id: str,
    tenant_id: str,
    *,
    reason: str,
    platform: Optional[str] = None,
) -> None:
    with get_connection(_get_db_path()) as conn:
        conn.execute(
            """UPDATE browser_sessions
               SET state = 'degraded'
               WHERE browser_session_id = ? AND tenant_id = ?""",
            (session_id, tenant_id),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
            (
                str(uuid.uuid4()),
                session_id,
                reason,
                json.dumps({"reason": reason, "platform": platform}),
            ),
        )
