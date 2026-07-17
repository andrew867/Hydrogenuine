"""Shared DSE tranche admission fixtures."""

from __future__ import annotations

from typing import Any

FIXTURE_CLOCK = "2026-06-13T22:00:00.000000Z"
FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

VALID_ADMISSION: dict[str, Any] = {
    "request_id": "dse-req-valid",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
}

MISSING_APPROVAL: dict[str, Any] = {
    "request_id": "dse-req-missing-approval",
    "operator_ref": None,
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
}

STALE_APPROVAL: dict[str, Any] = {
    "request_id": "dse-req-stale-approval",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": PAST_EXPIRY,
    "scope": "approve_change",
}

MISSING_IAM: dict[str, Any] = {
    "request_id": "dse-req-missing-iam",
    "operator_ref": "bob",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
}

MISSING_TIM: dict[str, Any] = {
    "request_id": "dse-req-missing-tim",
    "operator_ref": "op:local",
    "freshness_ref": None,
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
}

MISSING_GPP: dict[str, Any] = {
    "request_id": "dse-req-missing-gpp",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "requires_gpp": True,
    "gpp_permit_ref": None,
}

MISSING_UEAK: dict[str, Any] = {
    "request_id": "dse-req-missing-ueak",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "requires_ueak": True,
    "ueak_admission_ref": None,
}

SECRET_LEAK: dict[str, Any] = {
    "request_id": "dse-req-secret",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "payload": {"token": "sk-abcdefghijklmnopqrstuvwxyz123456"},
}


def refusal_bundle(bundle_id: str, admission: dict[str, Any]) -> dict[str, Any]:
    return {"bundle_id": bundle_id, "admission": admission}


__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "MISSING_APPROVAL",
    "MISSING_GPP",
    "MISSING_IAM",
    "MISSING_TIM",
    "MISSING_UEAK",
    "PAST_EXPIRY",
    "SECRET_LEAK",
    "STALE_APPROVAL",
    "VALID_ADMISSION",
    "refusal_bundle",
]
