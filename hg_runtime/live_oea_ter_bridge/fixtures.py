"""OEA-TER-LIVE fixtures — deterministic OEA/TER bridge bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_oea_ter_bridge.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

_VALID_DISPATCH_BASE: dict[str, Any] = {
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "requires_gpp": True,
    "requires_ueak": True,
    "gpp_permit_ref": "gpp:permit:fixture-valid",
    "ueak_admission_ref": "ueak:admission:fixture-valid",
    "rollback_plan_ref": "rollback:plan:fixture-valid",
    "observed_at": FIXTURE_CLOCK,
}

OEA_TER_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "oea-valid-dispatch",
        "notes": "valid dispatch candidate path with IAM TIM GPP UEAK and expiry",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-valid-dispatch",
            "external_surface": "fake",
            "action_digest": "digest:valid-dispatch",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-valid-http-surface",
        "notes": "valid http surface dispatch candidate",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-valid-http",
            "external_surface": "http",
            "action_digest": "digest:valid-http",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-valid-fs-surface",
        "notes": "valid fs surface dispatch candidate",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-valid-fs",
            "external_surface": "fs",
            "action_digest": "digest:valid-fs",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-missing-operator-approval",
        "notes": "missing operator approval refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-missing-approval",
            "external_surface": "fake",
            "action_digest": "digest:missing-approval",
            "operator_ref": None,
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-stale-approval",
        "notes": "stale approval refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-stale-approval",
            "external_surface": "fake",
            "action_digest": "digest:stale-approval",
            "approval_expires_at": PAST_EXPIRY,
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-missing-iam",
        "notes": "missing IAM refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-missing-iam",
            "external_surface": "fake",
            "action_digest": "digest:missing-iam",
            "operator_ref": "bob",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-missing-tim",
        "notes": "missing TIM freshness refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-missing-tim",
            "external_surface": "fake",
            "action_digest": "digest:missing-tim",
            "freshness_ref": "tim:missing",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-stale-tim",
        "notes": "stale TIM freshness refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-stale-tim",
            "external_surface": "fake",
            "action_digest": "digest:stale-tim",
            "freshness_ref": "tim:stale",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-missing-gpp",
        "notes": "missing GPP permit refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-missing-gpp",
            "external_surface": "fake",
            "action_digest": "digest:missing-gpp",
            "gpp_permit_ref": None,
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-missing-ueak",
        "notes": "missing UEAK admission refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-missing-ueak",
            "external_surface": "fake",
            "action_digest": "digest:missing-ueak",
            "ueak_admission_ref": None,
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-authority-conversion",
        "notes": "authority conversion refusal",
        "adversarial_signal": "authority_conversion",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-authority-conversion",
            "external_surface": "fake",
            "action_digest": "digest:authority-conversion",
            "treat_as_authority": True,
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-secret-leak",
        "notes": "secret redaction refusal",
        "adversarial_signal": "secret_leak",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-secret",
            "external_surface": "fake",
            "action_digest": "password=secret123",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-out-of-scope-live",
        "notes": "out of scope live action contained",
        "adversarial_signal": "out_of_scope_live",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-out-of-scope",
            "external_surface": "shell",
            "action_digest": "digest:out-of-scope",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-valid-rollback",
        "notes": "valid rollback after fake-sink commit",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-valid-rollback",
            "external_surface": "fake",
            "action_digest": "digest:rollback",
            "rollback_plan_ref": "rollback:plan:valid-rollback",
            "control_kind": "dispatch",
        },
    },
    {
        "bundle_id": "oea-valid-compensation",
        "notes": "valid compensation from rollback record",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-valid-compensation",
            "external_surface": "fake",
            "action_digest": "digest:compensation",
            "rollback_plan_ref": "rollback:plan:valid-compensation",
            "compensation_plan_ref": "compensation:plan:valid",
            "control_kind": "compensate",
        },
    },
    {
        "bundle_id": "oea-kill-switch",
        "notes": "kill switch panic refusal",
        "dispatch_request": {
            **_VALID_DISPATCH_BASE,
            "request_id": "oea-req-kill-switch",
            "external_surface": "fake",
            "action_digest": "digest:kill-switch",
            "control_kind": "panic",
            "kill_switch_active": True,
        },
    },
)


def load_oea_ter_fixtures() -> tuple[dict[str, Any], ...]:
    return OEA_TER_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "OEA_TER_FIXTURE_BUNDLES", "PAST_EXPIRY", "load_oea_ter_fixtures"]
