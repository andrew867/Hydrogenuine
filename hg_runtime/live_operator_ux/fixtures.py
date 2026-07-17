"""OUX-LIVE fixtures — deterministic operator console bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_operator_ux.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

OUX_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "oux-valid-approve",
        "notes": "valid approved fixture path with IAM TIM and expiry",
        "action_request": {
            "request_id": "oux-req-valid-approve",
            "review_item_ref": "ori-item:live-1",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-missing-operator-approval",
        "notes": "missing operator approval refusal",
        "action_request": {
            "request_id": "oux-req-missing-approval",
            "review_item_ref": "ori-item:live-2",
            "control_kind": "approve",
            "operator_ref": None,
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-stale-approval",
        "notes": "stale approval refusal",
        "action_request": {
            "request_id": "oux-req-stale-approval",
            "review_item_ref": "ori-item:live-3",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": PAST_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-missing-iam",
        "notes": "missing IAM refusal",
        "action_request": {
            "request_id": "oux-req-missing-iam",
            "review_item_ref": "ori-item:live-4",
            "control_kind": "approve",
            "operator_ref": "bob",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-missing-tim",
        "notes": "missing TIM freshness refusal",
        "action_request": {
            "request_id": "oux-req-missing-tim",
            "review_item_ref": "ori-item:live-5",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:missing",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-stale-tim",
        "notes": "stale TIM freshness refusal",
        "action_request": {
            "request_id": "oux-req-stale-tim",
            "review_item_ref": "ori-item:live-6",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:stale",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-missing-gpp",
        "notes": "missing GPP permit refusal where required",
        "action_request": {
            "request_id": "oux-req-missing-gpp",
            "review_item_ref": "ori-item:live-7",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "requires_gpp": True,
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-missing-ueak",
        "notes": "missing UEAK admission refusal where required",
        "action_request": {
            "request_id": "oux-req-missing-ueak",
            "review_item_ref": "ori-item:live-8",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "requires_ueak": True,
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-authority-conversion",
        "notes": "authority conversion refusal",
        "adversarial_signal": "authority_conversion",
        "action_request": {
            "request_id": "oux-req-authority-conversion",
            "review_item_ref": "ori-item:live-9",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "ui_display_state": "approved",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-secret-leak",
        "notes": "secret redaction refusal",
        "adversarial_signal": "secret_leak",
        "action_request": {
            "request_id": "oux-req-secret",
            "review_item_ref": "password=secret123",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-panic-as-permission",
        "notes": "panic signal grants execution",
        "adversarial_signal": "panic_as_permission",
        "action_request": {
            "request_id": "oux-req-panic-permission",
            "review_item_ref": "ori-item:live-10",
            "control_kind": "panic",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-valid-deny",
        "notes": "valid deny control",
        "action_request": {
            "request_id": "oux-req-valid-deny",
            "review_item_ref": "ori-item:live-11",
            "control_kind": "deny",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-valid-revoke",
        "notes": "valid revoke control",
        "action_request": {
            "request_id": "oux-req-valid-revoke",
            "review_item_ref": "ori-item:live-12",
            "control_kind": "revoke",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-valid-pause",
        "notes": "valid pause control",
        "action_request": {
            "request_id": "oux-req-valid-pause",
            "review_item_ref": "ori-item:live-13",
            "control_kind": "pause",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
    {
        "bundle_id": "oux-out-of-scope-live",
        "notes": "call oea ter outside scope",
        "adversarial_signal": "out_of_scope_live",
        "action_request": {
            "request_id": "oux-req-out-of-scope",
            "review_item_ref": "call oea ter now",
            "control_kind": "approve",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "observed_at": FIXTURE_CLOCK,
        },
    },
)


def load_oux_fixtures() -> tuple[dict[str, Any], ...]:
    return OUX_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "OUX_FIXTURE_BUNDLES", "PAST_EXPIRY", "load_oux_fixtures"]
