"""GMG-LIVE fixtures — deterministic grant authority bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.grant_authority_live.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"
PAST_GRANT_EXPIRY = "2026-06-13T14:00:00.000000Z"

_VALID_GRANT_BASE: dict[str, Any] = {
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "grant_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "requires_gpp": True,
    "requires_ueak": True,
    "gpp_permit_ref": "gpp:permit:fixture-valid",
    "ueak_admission_ref": "ueak:admission:fixture-valid",
    "rollback_plan_ref": "rollback:plan:fixture-valid",
    "observed_at": FIXTURE_CLOCK,
}

GMG_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "gmg-valid-tool-grant",
        "notes": "valid tool grant candidate path with IAM TIM GPP UEAK and expiry",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-valid-tool",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:read-only",
        },
    },
    {
        "bundle_id": "gmg-valid-memory-namespace-grant",
        "notes": "valid memory namespace grant candidate",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-valid-namespace",
            "grant_type": "memory_namespace",
            "control_kind": "issue",
            "namespace_ref": "mem-ns:fixture:session",
        },
    },
    {
        "bundle_id": "gmg-valid-context-grant",
        "notes": "valid context grant candidate",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-valid-context",
            "grant_type": "context",
            "control_kind": "issue",
            "context_scope": "ctx:fixture:review-queue",
        },
    },
    {
        "bundle_id": "gmg-valid-budget-grant",
        "notes": "valid budget grant candidate",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-valid-budget",
            "grant_type": "budget",
            "control_kind": "issue",
            "budget_limit": "budget:fixture:100-tokens",
        },
    },
    {
        "bundle_id": "gmg-missing-operator-approval",
        "notes": "missing operator approval refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-missing-approval",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:missing-approval",
            "operator_ref": None,
        },
    },
    {
        "bundle_id": "gmg-stale-approval",
        "notes": "stale approval refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-stale-approval",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:stale-approval",
            "approval_expires_at": PAST_EXPIRY,
        },
    },
    {
        "bundle_id": "gmg-missing-iam",
        "notes": "missing IAM refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-missing-iam",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:missing-iam",
            "operator_ref": "bob",
        },
    },
    {
        "bundle_id": "gmg-missing-tim",
        "notes": "missing TIM freshness refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-missing-tim",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:missing-tim",
            "freshness_ref": "tim:missing",
        },
    },
    {
        "bundle_id": "gmg-stale-tim",
        "notes": "stale TIM freshness refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-stale-tim",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:stale-tim",
            "freshness_ref": "tim:stale",
        },
    },
    {
        "bundle_id": "gmg-missing-gpp",
        "notes": "missing GPP permit refusal where required",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-missing-gpp",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:missing-gpp",
            "gpp_permit_ref": None,
        },
    },
    {
        "bundle_id": "gmg-missing-ueak",
        "notes": "missing UEAK admission refusal where required",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-missing-ueak",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:missing-ueak",
            "ueak_admission_ref": None,
        },
    },
    {
        "bundle_id": "gmg-authority-conversion",
        "notes": "authority conversion refusal",
        "adversarial_signal": "authority_conversion",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-authority-conversion",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:authority-conversion",
            "treat_as_authority": True,
        },
    },
    {
        "bundle_id": "gmg-secret-leak",
        "notes": "secret redaction refusal",
        "adversarial_signal": "secret_leak",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-secret",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "password=secret123",
        },
    },
    {
        "bundle_id": "gmg-out-of-scope-live",
        "notes": "call oea ter outside scope",
        "adversarial_signal": "out_of_scope_live",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-out-of-scope",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "call oea ter now",
        },
    },
    {
        "bundle_id": "gmg-valid-revoke",
        "notes": "valid revocation after fake-sink commit",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-valid-revoke",
            "grant_type": "tool",
            "control_kind": "revoke",
            "tool_ref": "tool:fixture:revoke-target",
        },
    },
    {
        "bundle_id": "gmg-expired-grant",
        "notes": "expired grant refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-expired-grant",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "tool:fixture:expired",
            "grant_expires_at": PAST_GRANT_EXPIRY,
        },
    },
    {
        "bundle_id": "gmg-ambient-grant",
        "notes": "ambient overbroad grant refusal",
        "grant_request": {
            **_VALID_GRANT_BASE,
            "request_id": "gmg-req-ambient",
            "grant_type": "tool",
            "control_kind": "issue",
            "tool_ref": "*",
            "scope": "*",
        },
    },
)


def load_gmg_fixtures() -> tuple[dict[str, Any], ...]:
    return GMG_FIXTURE_BUNDLES


__all__ = [
    "FUTURE_EXPIRY",
    "GMG_FIXTURE_BUNDLES",
    "PAST_EXPIRY",
    "PAST_GRANT_EXPIRY",
    "load_gmg_fixtures",
]
