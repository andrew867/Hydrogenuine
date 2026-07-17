"""
Facebook adapter with supervised login state handling.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional

from hg_core.browser.playwright_runtime import get_playwright_runtime
from hg_core.browser.runtime import BrowserRuntime
from hg_core.browser.session_health import (
    browser_session_is_reusable,
    evaluate_browser_session_health,
    mark_browser_session_degraded,
)
from hg_core.security import (
    KeystoreService,
    get_latest_bound_browser_session_id,
    get_default_provider,
    record_social_account_artifact,
    record_social_account_session_binding,
)
from hg_core.social.base import SocialAdapter, SocialDraft
from hg_gateway import keystore_repo


@dataclass
class FacebookLoginSecret:
    identifier: str
    password: str


@dataclass
class FacebookNotificationItem:
    title: str
    actor: str
    snippet: str
    href: Optional[str]
    timestamp_text: str
    kind: str


def parse_facebook_login_secret(secret: str) -> FacebookLoginSecret:
    """Parse the keystore login secret into identifier/password fields."""
    raw = (secret or "").strip()
    if "|" in raw:
        identifier, password = raw.split("|", 1)
    elif "\n" in raw:
        identifier, password = raw.split("\n", 1)
    else:
        raise ValueError("Facebook login secret must be formatted as identifier|password")
    identifier = identifier.strip()
    password = password.strip()
    if not identifier or not password:
        raise ValueError("Facebook login secret must include both identifier and password")
    return FacebookLoginSecret(identifier=identifier, password=password)


def detect_facebook_login_state(
    html: str,
    url: str = "",
    *,
    expected_account_alias: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify the current Facebook page state using deterministic markers."""
    doc = (html or "").lower()
    current_url = (url or "").lower()

    if "checkpoint" in current_url or "challenge" in current_url or "checkpoint" in doc or "security check" in doc:
        return {"state": "challenge", "reason": "challenge_detected"}

    has_login_form = (
        ("name=\"email\"" in doc or "id=\"email\"" in doc or "autocomplete=\"username\"" in doc)
        and ("name=\"pass\"" in doc or "id=\"pass\"" in doc or "autocomplete=\"current-password\"" in doc)
    )
    if has_login_form:
        return {"state": "login_required", "reason": "login_form_detected"}

    account_marker = None
    marker_key = 'data-authenticated-user="'
    if marker_key in doc:
        start = doc.index(marker_key) + len(marker_key)
        end = doc.find('"', start)
        if end > start:
            account_marker = doc[start:end].strip()

    logged_in_markers = (
        'aria-label="notifications"' in doc
        or 'href="/notifications"' in doc
        or 'data-pagelet="leftnav"' in doc
        or 'role="navigation"' in doc and "notifications" in doc
    )
    if logged_in_markers:
        if expected_account_alias and account_marker and account_marker != expected_account_alias.lower():
            return {
                "state": "wrong_account",
                "reason": "authenticated_account_mismatch",
                "authenticated_account": account_marker,
            }
        return {
            "state": "logged_in",
            "reason": "authenticated_markers_detected",
            "authenticated_account": account_marker,
        }

    return {"state": "unknown", "reason": "no_known_markers"}


def extract_facebook_notifications(html: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Extract visible notification items from synthetic or real-ish HTML."""
    doc = html or ""
    pattern = re.compile(
        r"<li[^>]*data-notification(?:-kind)?=\"(?P<kind>[^\"]*)\"[^>]*>"
        r".*?<span[^>]*class=\"actor\"[^>]*>(?P<actor>.*?)</span>"
        r".*?<span[^>]*class=\"title\"[^>]*>(?P<title>.*?)</span>"
        r".*?<span[^>]*class=\"snippet\"[^>]*>(?P<snippet>.*?)</span>"
        r".*?<span[^>]*class=\"timestamp\"[^>]*>(?P<timestamp>.*?)</span>"
        r".*?(?:<a[^>]*href=\"(?P<href>[^\"]*)\"[^>]*>)?",
        re.IGNORECASE | re.DOTALL,
    )
    items: List[Dict[str, Any]] = []
    for match in pattern.finditer(doc):
        groups = {k: (v or "").strip() for k, v in match.groupdict().items()}
        items.append(
            {
                "title": _strip_html(groups["title"]),
                "actor": _strip_html(groups["actor"]),
                "snippet": _strip_html(groups["snippet"]),
                "href": groups.get("href") or None,
                "timestamp_text": _strip_html(groups["timestamp"]),
                "kind": _strip_html(groups["kind"]) or "unknown",
            }
        )
        if len(items) >= limit:
            break
    return items


def build_notifications_digest(items: List[Dict[str, Any]]) -> str:
    """Build a short digest from extracted notifications."""
    if not items:
        return "No visible Facebook notifications."
    parts = []
    for item in items[:5]:
        actor = item.get("actor") or "Someone"
        title = item.get("title") or "sent a notification"
        snippet = item.get("snippet") or ""
        timestamp = item.get("timestamp_text") or "unknown time"
        text = f"{actor}: {title}"
        if snippet:
            text += f" ({snippet})"
        text += f" [{timestamp}]"
        parts.append(text)
    return " | ".join(parts)


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


class FacebookAdapter(SocialAdapter):
    platform = "facebook"

    def __init__(
        self,
        *,
        runtime: Optional[BrowserRuntime] = None,
        keystore: Optional[KeystoreService] = None,
    ) -> None:
        self._runtime = runtime or get_playwright_runtime()
        self._keystore = keystore or KeystoreService(get_default_provider())

    def search(self, query: str) -> List[Dict[str, Any]]:
        return [{"title": f"stub Facebook result for {query}", "uri": "https://facebook.com"}]

    def preview(self, draft: SocialDraft) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "action_type": draft.action_type,
            "rendered_preview": draft.content,
            "target_uri": draft.target_uri,
        }

    def submit(self, draft: SocialDraft, *, approval_id: str | None = None, approved: bool = False) -> Dict[str, Any]:
        if not approved:
            return {"platform": self.platform, "submitted": False, "blocked": True, "message": "blocked_until_approved"}
        return {"platform": self.platform, "action_type": draft.action_type, "submitted": True, "note": "Stub: wire Facebook API"}

    def _record_login_proof(
        self,
        *,
        resolved,
        tenant_id: str,
        entity_id: str,
        state: str,
        login_performed: bool,
        artifacts: Dict[str, Any],
        reason: Optional[str] = None,
        authenticated_account: Optional[str] = None,
    ) -> Dict[str, Any]:
        artifact_type = "verification_proof" if state == "logged_in" else "account_proof"
        return record_social_account_artifact(
            resolved.social_account_id,
            artifact_type=artifact_type,
            label=f"facebook-login-{state}",
            payload={
                "platform": self.platform,
                "tenant_id": tenant_id,
                "entity_id": entity_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": state,
                "reason": reason,
                "authenticated_account": authenticated_account,
                "login_performed": login_performed,
                "artifacts": artifacts,
            },
            metadata={
                "platform": self.platform,
                "state": state,
                "login_performed": login_performed,
                "account_alias": resolved.account_alias,
            },
        )

    def _get_or_start_session(
        self,
        *,
        resolved,
        tenant_id: str,
        entity_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if session_id:
            return {"browser_session_id": session_id, "replaced_degraded_session": None}
        bound_session_id = get_latest_bound_browser_session_id(resolved.social_account_id)
        replaced_degraded_session = None
        if bound_session_id:
            bound_state = self._runtime.get_session_state(bound_session_id, tenant_id=tenant_id)
            bound_artifacts = self._runtime.list_artifacts(bound_session_id, tenant_id=tenant_id)
            if self._is_reusable_session(bound_session_id, bound_state, bound_artifacts, tenant_id=tenant_id):
                return {"browser_session_id": bound_session_id, "replaced_degraded_session": None}
            if bound_state:
                bound_health = evaluate_browser_session_health(bound_state, bound_artifacts)
                mark_browser_session_degraded(
                    bound_session_id,
                    tenant_id,
                    reason="missing_restart_critical_browser_artifacts",
                    platform=self.platform,
                )
                replaced_degraded_session = {
                    "browser_session_id": bound_session_id,
                    "reason": "missing_restart_critical_browser_artifacts",
                    "previous_health": bound_health,
                }
        return {
            "browser_session_id": self._runtime.start_session(entity_id, self.platform, tenant_id=tenant_id),
            "replaced_degraded_session": replaced_degraded_session,
        }

    def _is_reusable_session(
        self,
        session_id: str,
        session_state: Optional[Dict[str, Any]],
        artifacts: List[Dict[str, Any]],
        *,
        tenant_id: str,
    ) -> bool:
        return browser_session_is_reusable(session_state, artifacts=artifacts)

    def _record_session_binding(
        self,
        *,
        resolved,
        tenant_id: str,
        entity_id: str,
        browser_session_id: str,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        return record_social_account_session_binding(
            resolved.social_account_id,
            browser_session_id=browser_session_id,
            platform=self.platform,
            tenant_id=tenant_id,
            entity_id=entity_id,
            account_alias=resolved.account_alias,
            state=state,
        )

    def login(
        self,
        *,
        tenant_id: str,
        entity_id: str,
        account_alias: Optional[str] = None,
        social_account_id: Optional[str] = None,
        session_id: Optional[str] = None,
        login_url: str = "https://www.facebook.com/",
    ) -> Dict[str, Any]:
        """Perform a supervised keystore-backed Facebook login attempt."""
        resolved = self._keystore.resolve_social_account(
            social_account_id=social_account_id,
            account_alias=account_alias,
            tenant_id=tenant_id,
            platform=self.platform,
            entity_id=entity_id,
        )
        secret = parse_facebook_login_secret(resolved.login_secret)
        session_info = self._get_or_start_session(
            resolved=resolved,
            tenant_id=tenant_id,
            entity_id=entity_id,
            session_id=session_id,
        )
        browser_session_id = session_info["browser_session_id"]
        replaced_degraded_session = session_info.get("replaced_degraded_session")
        session_binding = self._record_session_binding(
            resolved=resolved,
            tenant_id=tenant_id,
            entity_id=entity_id,
            browser_session_id=browser_session_id,
        )

        self._runtime.navigate(browser_session_id, login_url, tenant_id=tenant_id)
        before = self._runtime.capture(browser_session_id, "facebook-login-before", tenant_id=tenant_id)
        before_state = self._read_state(browser_session_id, resolved.account_alias, tenant_id=tenant_id)

        if before_state["state"] == "logged_in":
            keystore_repo.social_account_update_state(resolved.social_account_id, tenant_id, "verified")
            artifacts = {
                "before_screenshot": before.screenshot_path,
                "before_snapshot": before.snapshot_path,
            }
            proof = self._record_login_proof(
                resolved=resolved,
                tenant_id=tenant_id,
                entity_id=entity_id,
                state="logged_in",
                login_performed=False,
                artifacts=artifacts,
                reason=before_state.get("reason"),
                authenticated_account=before_state.get("authenticated_account"),
            )
            return {
                "platform": self.platform,
                "browser_session_id": browser_session_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": "logged_in",
                "artifacts": artifacts,
                "login_performed": False,
                "replaced_degraded_session": replaced_degraded_session,
                "account_proof_artifact": proof,
                "session_binding_artifact": session_binding,
            }

        if before_state["state"] == "challenge":
            keystore_repo.social_account_update_state(resolved.social_account_id, tenant_id, "challenged")
            self._runtime.pause_for_human_gate(browser_session_id, "facebook_login_challenge", tenant_id=tenant_id)
            artifacts = {
                "before_screenshot": before.screenshot_path,
                "before_snapshot": before.snapshot_path,
            }
            proof = self._record_login_proof(
                resolved=resolved,
                tenant_id=tenant_id,
                entity_id=entity_id,
                state="challenge",
                login_performed=False,
                artifacts=artifacts,
                reason=before_state.get("reason"),
                authenticated_account=before_state.get("authenticated_account"),
            )
            return {
                "platform": self.platform,
                "browser_session_id": browser_session_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": "challenge",
                "artifacts": artifacts,
                "login_performed": False,
                "replaced_degraded_session": replaced_degraded_session,
                "account_proof_artifact": proof,
                "session_binding_artifact": session_binding,
            }

        if before_state["state"] != "login_required":
            artifacts = {
                "before_screenshot": before.screenshot_path,
                "before_snapshot": before.snapshot_path,
            }
            proof = self._record_login_proof(
                resolved=resolved,
                tenant_id=tenant_id,
                entity_id=entity_id,
                state=before_state["state"],
                login_performed=False,
                artifacts=artifacts,
                reason=before_state.get("reason"),
                authenticated_account=before_state.get("authenticated_account"),
            )
            return {
                "platform": self.platform,
                "browser_session_id": browser_session_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": before_state["state"],
                "artifacts": artifacts,
                "login_performed": False,
                "replaced_degraded_session": replaced_degraded_session,
                "account_proof_artifact": proof,
                "session_binding_artifact": session_binding,
            }

        self._runtime.fill(browser_session_id, "input[name='email']", secret.identifier, tenant_id=tenant_id)
        self._runtime.fill(browser_session_id, "input[name='pass']", secret.password, tenant_id=tenant_id)
        self._runtime.click(browser_session_id, "button[name='login']", tenant_id=tenant_id)

        after = self._runtime.capture(browser_session_id, "facebook-login-after", tenant_id=tenant_id)
        after_state = self._read_state(browser_session_id, resolved.account_alias, tenant_id=tenant_id)
        if after_state["state"] == "logged_in":
            keystore_repo.social_account_update_state(resolved.social_account_id, tenant_id, "verified")
        elif after_state["state"] == "challenge":
            keystore_repo.social_account_update_state(resolved.social_account_id, tenant_id, "challenged")
            self._runtime.pause_for_human_gate(browser_session_id, "facebook_login_challenge", tenant_id=tenant_id)
        elif after_state["state"] == "wrong_account":
            keystore_repo.social_account_update_state(resolved.social_account_id, tenant_id, "locked")

        artifacts = {
            "before_screenshot": before.screenshot_path,
            "before_snapshot": before.snapshot_path,
            "after_screenshot": after.screenshot_path,
            "after_snapshot": after.snapshot_path,
        }
        proof = self._record_login_proof(
            resolved=resolved,
            tenant_id=tenant_id,
            entity_id=entity_id,
            state=after_state["state"],
            login_performed=True,
            artifacts=artifacts,
            reason=after_state.get("reason"),
            authenticated_account=after_state.get("authenticated_account"),
        )
        return {
            "platform": self.platform,
            "browser_session_id": browser_session_id,
            "social_account_id": resolved.social_account_id,
            "account_alias": resolved.account_alias,
            "state": after_state["state"],
            "reason": after_state.get("reason"),
            "authenticated_account": after_state.get("authenticated_account"),
            "artifacts": artifacts,
            "login_performed": True,
            "replaced_degraded_session": replaced_degraded_session,
            "account_proof_artifact": proof,
            "session_binding_artifact": session_binding,
        }

    def ensure_logged_in(
        self,
        *,
        tenant_id: str,
        entity_id: str,
        account_alias: Optional[str] = None,
        social_account_id: Optional[str] = None,
        session_id: str,
    ) -> Dict[str, Any]:
        """Ensure an existing session is authenticated, otherwise run login."""
        resolved = self._keystore.resolve_social_account(
            social_account_id=social_account_id,
            account_alias=account_alias,
            tenant_id=tenant_id,
            platform=self.platform,
            entity_id=entity_id,
        )
        state = self._read_state(session_id, resolved.account_alias, tenant_id=tenant_id)
        if state["state"] == "logged_in":
            return {
                "platform": self.platform,
                "browser_session_id": session_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": "logged_in",
                "login_performed": False,
            }
        return self.login(
            tenant_id=tenant_id,
            entity_id=entity_id,
            account_alias=resolved.account_alias,
            social_account_id=resolved.social_account_id,
            session_id=session_id,
        )

    def read_notifications(
        self,
        *,
        tenant_id: str,
        entity_id: str,
        account_alias: Optional[str] = None,
        social_account_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Read Facebook notifications and persist a digest artifact."""
        resolved = self._keystore.resolve_social_account(
            social_account_id=social_account_id,
            account_alias=account_alias,
            tenant_id=tenant_id,
            platform=self.platform,
            entity_id=entity_id,
        )
        session_info = self._get_or_start_session(
            resolved=resolved,
            tenant_id=tenant_id,
            entity_id=entity_id,
            session_id=session_id,
        )
        browser_session_id = session_info["browser_session_id"]
        replaced_degraded_session = session_info.get("replaced_degraded_session")
        session_binding = self._record_session_binding(
            resolved=resolved,
            tenant_id=tenant_id,
            entity_id=entity_id,
            browser_session_id=browser_session_id,
        )
        login_state = self.ensure_logged_in(
            tenant_id=tenant_id,
            entity_id=entity_id,
            account_alias=resolved.account_alias,
            social_account_id=resolved.social_account_id,
            session_id=browser_session_id,
        )
        if login_state["state"] != "logged_in":
            return {
                "platform": self.platform,
                "browser_session_id": browser_session_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": login_state["state"],
                "digest_text": "",
                "items": [],
                "notification_count_visible": 0,
                "artifacts": login_state.get("artifacts", {}),
                "replaced_degraded_session": login_state.get("replaced_degraded_session", replaced_degraded_session),
                "session_binding_artifact": session_binding,
            }

        self._runtime.navigate(browser_session_id, "https://www.facebook.com/notifications", tenant_id=tenant_id)
        before = self._runtime.capture(browser_session_id, "facebook-notifications-before", tenant_id=tenant_id)
        html = self._runtime.get_page_content(browser_session_id, tenant_id=tenant_id)
        page_state = self._read_state(browser_session_id, resolved.account_alias, tenant_id=tenant_id)
        if page_state["state"] != "logged_in":
            return {
                "platform": self.platform,
                "browser_session_id": browser_session_id,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "state": page_state["state"],
                "digest_text": "",
                "items": [],
                "notification_count_visible": 0,
                "artifacts": {
                    "before_screenshot": before.screenshot_path,
                    "before_snapshot": before.snapshot_path,
                },
                "replaced_degraded_session": replaced_degraded_session,
                "session_binding_artifact": session_binding,
            }
        items = extract_facebook_notifications(html, limit=limit)
        digest_text = build_notifications_digest(items)
        after = self._runtime.capture(browser_session_id, "facebook-notifications-after", tenant_id=tenant_id)
        digest_path = self._runtime.write_json_artifact(
            browser_session_id,
            "facebook-notifications-digest",
            {
                "platform": self.platform,
                "social_account_id": resolved.social_account_id,
                "account_alias": resolved.account_alias,
                "items": items,
                "digest_text": digest_text,
            },
            artifact_type="notification_digest",
            tenant_id=tenant_id,
        )
        return {
            "platform": self.platform,
            "browser_session_id": browser_session_id,
            "social_account_id": resolved.social_account_id,
            "account_alias": resolved.account_alias,
            "state": "logged_in",
            "notification_count_visible": len(items),
            "items": items,
            "digest_text": digest_text,
            "artifacts": {
                "before_screenshot": before.screenshot_path,
                "before_snapshot": before.snapshot_path,
                "after_screenshot": after.screenshot_path,
                "after_snapshot": after.snapshot_path,
                "digest_path": digest_path,
            },
            "replaced_degraded_session": replaced_degraded_session,
            "challenge_state": None,
            "account_verified": True,
            "session_binding_artifact": session_binding,
        }

    def _read_state(self, session_id: str, account_alias: str, *, tenant_id: str) -> Dict[str, Any]:
        html = self._runtime.get_page_content(session_id, tenant_id=tenant_id)
        state = self._runtime.get_session_state(session_id, tenant_id=tenant_id) or {}
        return detect_facebook_login_state(
            html,
            state.get("current_url") or state.get("platform") or "",
            expected_account_alias=account_alias,
        )
