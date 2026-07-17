"""SEN-LIVE fixtures — deterministic sensor ingestion bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_sensor_ingestion.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

_BASE_VALID = {
    "modality": "text",
    "observation_digest": "digest:valid-ingest",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "consent_ref": "consent:fixture:valid",
    "redaction_policy_ref": "redaction:policy:fixture",
    "observed_at": FIXTURE_CLOCK,
}

SEN_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "sen-valid-ingest",
        "notes": "valid observation candidate path with IAM TIM consent and redaction",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-valid-ingest"},
    },
    {
        "bundle_id": "sen-missing-operator-approval",
        "notes": "missing operator approval refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-approval", "operator_ref": None},
    },
    {
        "bundle_id": "sen-stale-approval",
        "notes": "stale approval refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-stale-approval", "approval_expires_at": PAST_EXPIRY},
    },
    {
        "bundle_id": "sen-missing-iam",
        "notes": "missing IAM refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-iam", "operator_ref": "bob"},
    },
    {
        "bundle_id": "sen-missing-tim",
        "notes": "missing TIM freshness refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-tim", "freshness_ref": "tim:missing"},
    },
    {
        "bundle_id": "sen-stale-tim",
        "notes": "stale TIM freshness refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-stale-tim", "freshness_ref": "tim:stale"},
    },
    {
        "bundle_id": "sen-missing-gpp",
        "notes": "missing GPP permit refusal where required",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-gpp", "requires_gpp": True},
    },
    {
        "bundle_id": "sen-missing-ueak",
        "notes": "missing UEAK admission refusal where required",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-ueak", "requires_ueak": True},
    },
    {
        "bundle_id": "sen-missing-consent",
        "notes": "missing consent ref refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-consent", "consent_ref": None},
    },
    {
        "bundle_id": "sen-missing-redaction-policy",
        "notes": "missing redaction policy refusal",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-missing-redaction", "redaction_policy_ref": None},
    },
    {
        "bundle_id": "sen-valid-scalar-refusal",
        "notes": "refuse raw scalar as truth",
        "ingest_request": {
            **_BASE_VALID,
            "request_id": "sen-req-scalar-truth",
            "modality": "scalar",
            "observation_digest": "scalar:truth:raw_reading",
        },
    },
    {
        "bundle_id": "sen-authority-conversion",
        "notes": "authority conversion refusal",
        "adversarial_signal": "authority_conversion",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-authority-conversion", "treat_as_authority": True},
    },
    {
        "bundle_id": "sen-secret-leak",
        "notes": "secret redaction refusal",
        "adversarial_signal": "secret_leak",
        "ingest_request": {
            **_BASE_VALID,
            "request_id": "sen-req-secret",
            "observation_digest": "password=secret123",
        },
    },
    {
        "bundle_id": "sen-out-of-scope-live",
        "notes": "connect sensor now outside scope",
        "adversarial_signal": "out_of_scope_live",
        "ingest_request": {
            **_BASE_VALID,
            "request_id": "sen-req-out-of-scope",
            "observation_digest": "connect sensor now",
        },
    },
    {
        "bundle_id": "sen-valid-quarantine",
        "notes": "valid quarantine and withdrawal path",
        "ingest_request": {**_BASE_VALID, "request_id": "sen-req-valid-quarantine"},
    },
)


def load_sen_fixtures() -> tuple[dict[str, Any], ...]:
    return SEN_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "PAST_EXPIRY", "SEN_FIXTURE_BUNDLES", "load_sen_fixtures"]
