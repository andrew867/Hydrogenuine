"""
Browser runtime session abstraction and proof hooks (Social Media Entity Tools).
Start session, screenshot, pause_for_human_gate, close_session; persist in gateway DB (browser_sessions, proof_artifacts).
Playwright-backed implementation: use get_browser_runtime() which returns a stub that writes paths;
optional hg_core.browser.playwright_runtime can be wired when Playwright is installed.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class BrowserActionResult:
    ok: bool
    screenshot_path: Optional[str] = None
    trace_path: Optional[str] = None
    snapshot_path: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


def _artifacts_root() -> Path:
    root = os.environ.get("HG_BROWSER_ARTIFACTS_DIR") or "memory/artifacts/browser"
    return Path(root).expanduser().resolve()


def _get_db_path() -> str:
    return os.environ.get("HG_GATEWAY_DB_PATH") or str(Path("memory/gateway.sqlite3").expanduser().resolve())


class BrowserRuntime:
    """
    Session abstraction for supervised browser use. Persists browser_sessions and proof_artifacts in gateway DB.
    Use a real implementation (e.g. Playwright) in Phase 5.2; this provides the interface and persistence.
    """

    def __init__(self, db_path: Optional[str] = None, artifacts_dir: Optional[Path] = None) -> None:
        self._db_path = db_path or _get_db_path()
        self._artifacts_dir = artifacts_dir or _artifacts_root()

    def start_session(self, entity_id: str, platform: str, tenant_id: str = "default") -> str:
        """Create a browser session row and return session_id."""
        session_id = str(uuid.uuid4())
        self._insert_session(session_id, entity_id, platform, tenant_id=tenant_id)
        return session_id

    def find_reusable_session(
        self,
        entity_id: str,
        platform: str,
        *,
        tenant_id: str = "default",
        allowed_states: Optional[set[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the most recent non-closed session that can be reused."""
        states = allowed_states or {"active", "awaiting_human"}
        if not states:
            return None
        placeholders = ", ".join("?" for _ in states)
        params = [tenant_id, entity_id, platform, *sorted(states)]
        try:
            from hg_gateway.db import get_connection
            with get_connection(self._db_path) as conn:
                row = conn.execute(
                    f"""SELECT browser_session_id, tenant_id, entity_id, platform, state, started_at, ended_at, trace_path, latest_screenshot_path
                        FROM browser_sessions
                        WHERE tenant_id = ? AND entity_id = ? AND platform = ? AND state IN ({placeholders})
                        ORDER BY started_at DESC, browser_session_id DESC
                        LIMIT 1""",
                    tuple(params),
                ).fetchone()
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
        except Exception:
            return None

    def _insert_session(self, session_id: str, entity_id: str, platform: str, tenant_id: str = "default") -> None:
        """Persist an active browser session row."""
        try:
            from hg_gateway.db import get_connection
            with get_connection(self._db_path) as conn:
                conn.execute(
                    """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
                       VALUES (?, ?, ?, ?, 'active', datetime('now'))""",
                    (session_id, tenant_id, entity_id, platform),
                )
        except Exception:
            pass

    def screenshot(self, session_id: str, label: str, tenant_id: str = "default") -> str:
        """Record screenshot path for session; create proof_artifact. Returns path (stub path if no real capture)."""
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = str(self._artifacts_dir / f"{session_id}" / f"{label}.png")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).touch()
        self._update_session(session_id, tenant_id=tenant_id, latest_screenshot_path=path)
        self._register_artifact(
            session_id,
            artifact_type="screenshot",
            path=path,
            tenant_id=tenant_id,
            metadata={"label": label},
        )
        return path

    def navigate(self, session_id: str, url: str, tenant_id: str = "default") -> BrowserActionResult:
        """Navigate browser session to a URL. Stub runtime only records metadata."""
        self._register_artifact(
            session_id,
            artifact_type="navigate",
            path=url,
            tenant_id=tenant_id,
            metadata={"url": url},
        )
        return BrowserActionResult(ok=True, data={"url": url})

    def fill(self, session_id: str, selector: str, value: str, tenant_id: str = "default") -> BrowserActionResult:
        """Fill an input field. Stub runtime only records the action."""
        self._register_artifact(
            session_id,
            artifact_type="fill",
            path=selector,
            tenant_id=tenant_id,
            metadata={"selector": selector, "value_present": bool(value)},
        )
        return BrowserActionResult(ok=True, data={"selector": selector})

    def click(self, session_id: str, selector: str, tenant_id: str = "default") -> BrowserActionResult:
        """Click a page element. Stub runtime only records the action."""
        self._register_artifact(
            session_id,
            artifact_type="click",
            path=selector,
            tenant_id=tenant_id,
            metadata={"selector": selector},
        )
        return BrowserActionResult(ok=True, data={"selector": selector})

    def get_page_content(self, session_id: str, tenant_id: str = "default") -> str:
        """Return the current page content. Stub runtime returns an empty document."""
        return "<html></html>"

    def write_json_artifact(
        self,
        session_id: str,
        label: str,
        payload: Dict[str, Any],
        *,
        artifact_type: str = "snapshot",
        tenant_id: str = "default",
    ) -> str:
        """Write a JSON artifact and register it against the browser session."""
        return self._write_snapshot(
            session_id,
            label,
            payload,
            artifact_type=artifact_type,
            tenant_id=tenant_id,
        )

    def capture(self, session_id: str, label: str, tenant_id: str = "default") -> BrowserActionResult:
        """Capture a screenshot and a simple HTML snapshot placeholder."""
        screenshot_path = self.screenshot(session_id, label, tenant_id=tenant_id)
        snapshot_path = self.write_json_artifact(
            session_id,
            label,
            {"label": label, "session_id": session_id, "mode": "stub"},
            artifact_type="snapshot",
            tenant_id=tenant_id,
        )
        return BrowserActionResult(
            ok=True,
            screenshot_path=screenshot_path,
            snapshot_path=snapshot_path,
            data={"label": label},
        )

    def pause_for_human_gate(self, session_id: str, reason: str, tenant_id: str = "default") -> None:
        """Mark a browser session as awaiting operator input."""
        self._update_session(session_id, tenant_id=tenant_id, state="awaiting_human")
        self._register_artifact(
            session_id,
            artifact_type="pause",
            path=reason,
            tenant_id=tenant_id,
            metadata={"reason": reason},
        )

    def resume_session(self, session_id: str, tenant_id: str = "default") -> None:
        """Resume a paused browser session."""
        self._update_session(session_id, tenant_id=tenant_id, state="active")
        self._register_artifact(
            session_id,
            artifact_type="resume",
            path=session_id,
            tenant_id=tenant_id,
            metadata={"resumed": True},
        )

    def close_session(self, session_id: str, trace_path: Optional[str] = None, tenant_id: str = "default") -> None:
        """End session; update browser_sessions.ended_at and optional trace_path."""
        self._update_session(
            session_id,
            tenant_id=tenant_id,
            state="closed",
            trace_path=trace_path,
            ended=True,
        )
        if trace_path:
            self._register_artifact(
                session_id,
                artifact_type="trace",
                path=trace_path,
                tenant_id=tenant_id,
                metadata={},
            )

    def get_session_state(self, session_id: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """Fetch the persisted browser session row."""
        try:
            from hg_gateway.db import get_connection
            with get_connection(self._db_path) as conn:
                row = conn.execute(
                    """SELECT browser_session_id, tenant_id, entity_id, platform, state, started_at, ended_at, trace_path, latest_screenshot_path
                       FROM browser_sessions WHERE browser_session_id = ? AND tenant_id = ?""",
                    (session_id, tenant_id),
                ).fetchone()
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
        except Exception:
            return None

    def list_artifacts(self, session_id: str, tenant_id: str = "default") -> list[Dict[str, Any]]:
        """List proof artifacts bound to a browser session."""
        try:
            from hg_gateway.db import get_connection
            with get_connection(self._db_path) as conn:
                rows = conn.execute(
                    """SELECT proof_id, artifact_type, path, metadata_json, created_at
                       FROM proof_artifacts
                       WHERE related_kind = 'browser_session' AND related_id = ?
                       ORDER BY created_at, proof_id""",
                    (session_id,),
                ).fetchall()
                return [
                    {
                        "proof_id": row[0],
                        "artifact_type": row[1],
                        "path": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {},
                        "created_at": row[4],
                    }
                    for row in rows
                ]
        except Exception:
            return []

    def get_latest_artifact(
        self,
        session_id: str,
        artifact_type: str,
        *,
        tenant_id: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """Return the newest artifact of a given type for the browser session."""
        items = self.list_artifacts(session_id, tenant_id=tenant_id)
        for item in items:
            if item.get("artifact_type") == artifact_type:
                return item
        return None

    def _write_snapshot(
        self,
        session_id: str,
        label: str,
        payload: Dict[str, Any],
        *,
        artifact_type: str = "snapshot",
        tenant_id: str = "default",
    ) -> str:
        """Write a JSON snapshot artifact and register it."""
        path = self._artifacts_dir / f"{session_id}" / f"{label}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._register_artifact(
            session_id,
            artifact_type=artifact_type,
            path=str(path),
            tenant_id=tenant_id,
            metadata={"label": label},
        )
        return str(path)

    def _register_artifact(
        self,
        session_id: str,
        *,
        artifact_type: str,
        path: str,
        tenant_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a proof artifact row for the browser session."""
        try:
            from hg_gateway.db import get_connection
            with get_connection(self._db_path) as conn:
                proof_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
                       VALUES (?, 'browser_session', ?, ?, ?, ?, datetime('now'))""",
                    (proof_id, session_id, artifact_type, path, json.dumps(metadata or {})),
                )
        except Exception:
            pass

    def _update_session(
        self,
        session_id: str,
        *,
        tenant_id: str = "default",
        state: Optional[str] = None,
        latest_screenshot_path: Optional[str] = None,
        trace_path: Optional[str] = None,
        ended: bool = False,
    ) -> None:
        """Update mutable browser session fields."""
        updates: list[str] = []
        values: list[Any] = []
        if state is not None:
            updates.append("state = ?")
            values.append(state)
        if latest_screenshot_path is not None:
            updates.append("latest_screenshot_path = ?")
            values.append(latest_screenshot_path)
        if trace_path is not None:
            updates.append("trace_path = ?")
            values.append(trace_path)
        if ended:
            updates.append("ended_at = datetime('now')")
        if not updates:
            return
        values.extend([session_id, tenant_id])
        try:
            from hg_gateway.db import get_connection
            with get_connection(self._db_path) as conn:
                conn.execute(
                    f"UPDATE browser_sessions SET {', '.join(updates)} WHERE browser_session_id = ? AND tenant_id = ?",
                    tuple(values),
                )
        except Exception:
            pass
