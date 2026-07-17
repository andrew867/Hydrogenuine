"""Web action policy classifier — cargo not command."""

from __future__ import annotations

from hg_runtime.web_action_queue.action_types import DENIED_BY_DEFAULT, WebActionType
from hg_runtime.web_action_queue.schema import WebActionDecisionKind, WebActionPolicy
from hg_runtime.web_action_queue.sanitization import WebActionSanitizer


def classify_web_policy(
    action_type: WebActionType,
    *,
    trust_boundary_verdict: str = "UNKNOWN",
    live_browser_enabled: bool = False,
    cargo_text: str | None = None,
    stop_active: bool = False,
    panic_active: bool = False,
    prompt_injection: bool | None = None,
) -> WebActionPolicy:
    if panic_active:
        return WebActionPolicy(
            WebActionDecisionKind.BLOCKED_BY_PANIC,
            "panic active; no new web side effects",
            live_browser_enabled=live_browser_enabled,
        )
    if stop_active:
        return WebActionPolicy(
            WebActionDecisionKind.BLOCKED_BY_STOP,
            "stop active; approval and side effects blocked",
            live_browser_enabled=live_browser_enabled,
        )

    injection = prompt_injection if prompt_injection is not None else WebActionSanitizer.detect_prompt_injection(cargo_text)
    if injection:
        return WebActionPolicy(
            WebActionDecisionKind.BLOCKED_BY_TRUST_BOUNDARY,
            "prompt-injection suspected; cargo cannot command",
            live_browser_enabled=live_browser_enabled,
        )

    if WebActionSanitizer.detect_cargo_authorizes(cargo_text):
        return WebActionPolicy(
            WebActionDecisionKind.BLOCKED_BY_TRUST_BOUNDARY,
            "page content cannot authorize actions",
            live_browser_enabled=live_browser_enabled,
        )

    if trust_boundary_verdict.startswith("RED"):
        return WebActionPolicy(
            WebActionDecisionKind.BLOCKED_BY_TRUST_BOUNDARY,
            f"trust boundary: {trust_boundary_verdict}",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type in DENIED_BY_DEFAULT:
        return WebActionPolicy(
            WebActionDecisionKind.DENY_BY_DEFAULT,
            f"{action_type.value} denied by default in Phase 3",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type == WebActionType.WEB_FORM_SUBMIT:
        return WebActionPolicy(
            WebActionDecisionKind.FUTURE_PHASE_REQUIRED,
            "form submit not enabled in Phase 3",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type == WebActionType.WEB_LOGIN:
        return WebActionPolicy(
            WebActionDecisionKind.FUTURE_PHASE_REQUIRED,
            "login not enabled in Phase 3",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type in (WebActionType.WEB_PURCHASE, WebActionType.WEB_ACCOUNT_CHANGE, WebActionType.WEB_UPLOAD):
        return WebActionPolicy(
            WebActionDecisionKind.DENY_BY_DEFAULT,
            f"{action_type.value} denied in Phase 3",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type == WebActionType.WEB_DOWNLOAD_FILE:
        return WebActionPolicy(
            WebActionDecisionKind.QUARANTINE_DOWNLOAD,
            "download requires quarantine and operator review",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type in (WebActionType.WEB_READ_URL, WebActionType.WEB_SEARCH, WebActionType.WEB_EXTRACT_TEXT):
        if live_browser_enabled and trust_boundary_verdict.startswith("GREEN"):
            return WebActionPolicy(
                WebActionDecisionKind.ALLOW_READ_ONLY,
                "read-only web action permitted by policy",
                live_browser_enabled=True,
            )
        return WebActionPolicy(
            WebActionDecisionKind.QUEUE_FOR_OPERATOR,
            "live browser disabled or trust unknown; queued for operator",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type == WebActionType.WEB_SCREENSHOT:
        return WebActionPolicy(
            WebActionDecisionKind.ALLOW_READ_ONLY,
            "screenshot read-only if sanitized",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type in (WebActionType.WEB_CLICK_LINK, WebActionType.WEB_OPEN_IN_BROWSER):
        return WebActionPolicy(
            WebActionDecisionKind.QUEUE_FOR_OPERATOR,
            "navigation requires operator review",
            live_browser_enabled=live_browser_enabled,
        )

    if action_type == WebActionType.WEB_FORM_FILL:
        return WebActionPolicy(
            WebActionDecisionKind.DRY_RUN_ONLY,
            "form fill is draft/preview only",
            live_browser_enabled=live_browser_enabled,
        )

    return WebActionPolicy(
        WebActionDecisionKind.QUEUE_FOR_OPERATOR,
        "default queue for operator review",
        live_browser_enabled=live_browser_enabled,
    )


def requires_operator_queue(policy: WebActionPolicy) -> bool:
    return policy.decision in {
        WebActionDecisionKind.QUEUE_FOR_OPERATOR,
        WebActionDecisionKind.QUARANTINE_DOWNLOAD,
        WebActionDecisionKind.DRY_RUN_ONLY,
    }


def is_denied(policy: WebActionPolicy) -> bool:
    return policy.decision in {
        WebActionDecisionKind.DENY_BY_DEFAULT,
        WebActionDecisionKind.FUTURE_PHASE_REQUIRED,
        WebActionDecisionKind.BLOCKED_BY_TRUST_BOUNDARY,
        WebActionDecisionKind.BLOCKED_BY_STOP,
        WebActionDecisionKind.BLOCKED_BY_PANIC,
    }


__all__ = [
    "classify_web_policy",
    "is_denied",
    "requires_operator_queue",
]
