"""Source grounding policy — default-deny, read-only when enabled."""

from __future__ import annotations


DEFAULT_POLICY = {
    "browser_enabled": False,
    "mcp_enabled": False,
    "read_only": True,
    "login_allowed": False,
    "registration_allowed": False,
    "posting_allowed": False,
    "form_submit_allowed": False,
    "download_execute_allowed": False,
    "remote_provider_fallback_allowed": False,
}


def create_policy(**overrides) -> dict:
    policy = dict(DEFAULT_POLICY)
    policy.update(overrides)
    return policy


def check_request(policy: dict, request: dict) -> dict:
    """Evaluate a source request against policy. Returns decision."""
    denied_reasons = []

    if not policy.get("browser_enabled") and not policy.get("mcp_enabled"):
        denied_reasons.append("browser_and_mcp_disabled")

    if request.get("requires_login") and not policy.get("login_allowed"):
        denied_reasons.append("login_not_allowed")

    if not request.get("read_only", True) and policy.get("read_only", True):
        denied_reasons.append("write_not_allowed_in_read_only_mode")

    if request.get("requires_registration"):
        denied_reasons.append("registration_not_allowed")

    if request.get("requires_form_submit") and not policy.get("form_submit_allowed"):
        denied_reasons.append("form_submit_not_allowed")

    if request.get("requires_posting") and not policy.get("posting_allowed"):
        denied_reasons.append("posting_not_allowed")

    allowed = len(denied_reasons) == 0
    return {
        "allowed": allowed,
        "denied_reasons": denied_reasons,
        "runtime_decision": "allow" if allowed else "deny",
        "external_effect_authorized": False,
    }
