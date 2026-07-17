"""
Playwright-backed browser runtime.

Uses a persistent Chromium context per session directory, records screenshots/snapshots,
and stores session artifacts through the base BrowserRuntime helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.sync_api import sync_playwright

from hg_core.browser.runtime import BrowserActionResult, BrowserRuntime


@dataclass
class _SessionHandle:
    playwright: Any
    browser_context: Any
    page: Any
    profile_dir: Path
    tenant_id: str
    entity_id: str
    platform: str


class PlaywrightBrowserRuntime(BrowserRuntime):
    """Real browser runtime using Playwright persistent Chromium contexts."""

    def __init__(self, db_path: Optional[str] = None, artifacts_dir: Optional[Path] = None) -> None:
        super().__init__(db_path=db_path, artifacts_dir=artifacts_dir)
        self._sessions: dict[str, _SessionHandle] = {}

    def start_session(self, entity_id: str, platform: str, tenant_id: str = "default") -> str:
        session_id = super().start_session(entity_id, platform, tenant_id=tenant_id)
        session_root = self._artifacts_dir / session_id
        profile_dir = session_root / "profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
        )
        try:
            context.tracing.start(screenshots=True, snapshots=True)
        except Exception:
            pass
        page = context.pages[0] if context.pages else context.new_page()
        self._sessions[session_id] = _SessionHandle(
            playwright=playwright,
            browser_context=context,
            page=page,
            profile_dir=profile_dir,
            tenant_id=tenant_id,
            entity_id=entity_id,
            platform=platform,
        )
        self._register_artifact(
            session_id,
            artifact_type="profile_dir",
            path=str(profile_dir),
            tenant_id=tenant_id,
            metadata={"platform": platform},
        )
        return session_id

    def navigate(self, session_id: str, url: str, tenant_id: str = "default") -> BrowserActionResult:
        handle = self._require_session(session_id, tenant_id)
        response = handle.page.goto(url, wait_until="domcontentloaded")
        self._register_artifact(
            session_id,
            artifact_type="navigate",
            path=url,
            tenant_id=tenant_id,
            metadata={"status": getattr(response, "status", None)},
        )
        return BrowserActionResult(ok=True, data={"url": handle.page.url})

    def fill(self, session_id: str, selector: str, value: str, tenant_id: str = "default") -> BrowserActionResult:
        handle = self._require_session(session_id, tenant_id)
        handle.page.locator(selector).first.fill(value)
        self._register_artifact(
            session_id,
            artifact_type="fill",
            path=selector,
            tenant_id=tenant_id,
            metadata={"selector": selector, "value_present": bool(value)},
        )
        return BrowserActionResult(ok=True, data={"selector": selector})

    def click(self, session_id: str, selector: str, tenant_id: str = "default") -> BrowserActionResult:
        handle = self._require_session(session_id, tenant_id)
        handle.page.locator(selector).first.click()
        self._register_artifact(
            session_id,
            artifact_type="click",
            path=selector,
            tenant_id=tenant_id,
            metadata={"selector": selector},
        )
        return BrowserActionResult(ok=True, data={"selector": selector})

    def get_page_content(self, session_id: str, tenant_id: str = "default") -> str:
        handle = self._require_session(session_id, tenant_id)
        return handle.page.content()

    def screenshot(self, session_id: str, label: str, tenant_id: str = "default") -> str:
        handle = self._require_session(session_id, tenant_id)
        path = self._artifacts_dir / session_id / f"{label}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        handle.page.screenshot(path=str(path), full_page=True)
        self._update_session(session_id, tenant_id=tenant_id, latest_screenshot_path=str(path))
        self._register_artifact(
            session_id,
            artifact_type="screenshot",
            path=str(path),
            tenant_id=tenant_id,
            metadata={"label": label, "url": handle.page.url},
        )
        return str(path)

    def capture(self, session_id: str, label: str, tenant_id: str = "default") -> BrowserActionResult:
        handle = self._require_session(session_id, tenant_id)
        screenshot_path = self.screenshot(session_id, label, tenant_id=tenant_id)
        snapshot_path = self._write_snapshot(
            session_id,
            label,
            {"label": label, "url": handle.page.url, "html": handle.page.content()},
            tenant_id=tenant_id,
        )
        return BrowserActionResult(
            ok=True,
            screenshot_path=screenshot_path,
            snapshot_path=snapshot_path,
            data={"url": handle.page.url},
        )

    def pause_for_human_gate(self, session_id: str, reason: str, tenant_id: str = "default") -> None:
        self._require_session(session_id, tenant_id)
        super().pause_for_human_gate(session_id, reason, tenant_id=tenant_id)

    def resume_session(self, session_id: str, tenant_id: str = "default") -> None:
        self._require_session(session_id, tenant_id)
        super().resume_session(session_id, tenant_id=tenant_id)

    def close_session(self, session_id: str, trace_path: Optional[str] = None, tenant_id: str = "default") -> None:
        handle = self._sessions.pop(session_id, None)
        if handle:
            if trace_path is None:
                trace_path = str(self._artifacts_dir / session_id / "trace.zip")
            Path(trace_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                handle.browser_context.tracing.stop(path=str(trace_path))
            except Exception:
                trace_path = None
            try:
                handle.browser_context.close()
            finally:
                handle.playwright.stop()
        super().close_session(session_id, trace_path=trace_path, tenant_id=tenant_id)

    def get_session_state(self, session_id: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        state = super().get_session_state(session_id, tenant_id=tenant_id)
        handle = self._sessions.get(session_id)
        if state:
            if handle:
                state["current_url"] = handle.page.url
                state["profile_dir"] = str(handle.profile_dir)
            else:
                profile_artifact = self.get_latest_artifact(session_id, "profile_dir", tenant_id=tenant_id)
                if profile_artifact:
                    state["profile_dir"] = profile_artifact["path"]
        return state

    def _require_session(self, session_id: str, tenant_id: str) -> _SessionHandle:
        handle = self._sessions.get(session_id)
        if handle and handle.tenant_id == tenant_id:
            return handle
        restored = self._restore_session(session_id, tenant_id)
        if restored is None:
            raise KeyError(f"Browser session not active: {session_id}")
        return restored

    def _restore_session(self, session_id: str, tenant_id: str) -> Optional[_SessionHandle]:
        state = super().get_session_state(session_id, tenant_id=tenant_id)
        if not state:
            return None
        if state.get("state") == "closed":
            return None
        profile_artifact = self.get_latest_artifact(session_id, "profile_dir", tenant_id=tenant_id)
        profile_dir = Path(profile_artifact["path"]) if profile_artifact and profile_artifact.get("path") else None
        if not profile_dir or not profile_dir.exists():
            return None
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
        )
        try:
            context.tracing.start(screenshots=True, snapshots=True)
        except Exception:
            pass
        page = context.pages[0] if context.pages else context.new_page()
        handle = _SessionHandle(
            playwright=playwright,
            browser_context=context,
            page=page,
            profile_dir=profile_dir,
            tenant_id=tenant_id,
            entity_id=state["entity_id"],
            platform=state["platform"],
        )
        self._sessions[session_id] = handle
        self._register_artifact(
            session_id,
            artifact_type="session_restore",
            path=str(profile_dir),
            tenant_id=tenant_id,
            metadata={"restored": True, "platform": state["platform"]},
        )
        return handle
        return handle
