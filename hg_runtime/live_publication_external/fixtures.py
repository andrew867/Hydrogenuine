"""PUB-EXT-LIVE fixtures — deterministic publication external action bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_publication_external.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

_BASE_VALID = {
    "release_kind": "publish",
    "content_digest": "digest:valid-release",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "disclosure_policy_ref": "disclosure:policy:fixture",
    "redaction_policy_ref": "redaction:policy:fixture",
    "rollback_plan_ref": "rollback:plan:fixture",
    "withdrawal_plan_ref": "withdrawal:plan:fixture",
    "observed_at": FIXTURE_CLOCK,
}

PUB_EXT_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {"bundle_id": "pub-ext-valid-release", "notes": "valid release candidate", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-valid"}},
    {"bundle_id": "pub-ext-missing-operator-approval", "notes": "missing operator", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-approval", "operator_ref": None}},
    {"bundle_id": "pub-ext-stale-approval", "notes": "stale approval", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-stale", "approval_expires_at": PAST_EXPIRY}},
    {"bundle_id": "pub-ext-missing-iam", "notes": "missing IAM", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-iam", "operator_ref": "bob"}},
    {"bundle_id": "pub-ext-missing-tim", "notes": "missing TIM", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-tim", "freshness_ref": "tim:missing"}},
    {"bundle_id": "pub-ext-stale-tim", "notes": "stale TIM", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-stale-tim", "freshness_ref": "tim:stale"}},
    {"bundle_id": "pub-ext-missing-gpp", "notes": "missing GPP", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-gpp", "requires_gpp": True}},
    {"bundle_id": "pub-ext-missing-ueak", "notes": "missing UEAK", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-ueak", "requires_ueak": True}},
    {"bundle_id": "pub-ext-missing-disclosure-policy", "notes": "missing disclosure", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-disclosure", "disclosure_policy_ref": None}},
    {"bundle_id": "pub-ext-missing-rollback-plan", "notes": "missing rollback", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-rollback", "rollback_plan_ref": None}},
    {"bundle_id": "pub-ext-missing-withdrawal-plan", "notes": "missing withdrawal", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-missing-withdrawal", "withdrawal_plan_ref": None}},
    {"bundle_id": "pub-ext-irreversible-without-ack", "notes": "irreversible without ack", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-irreversible", "irreversible": True, "irreversible_ack": False}},
    {"bundle_id": "pub-ext-authority-conversion", "notes": "authority conversion", "adversarial_signal": "authority_conversion", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-authority", "treat_as_authority": True}},
    {"bundle_id": "pub-ext-secret-leak", "notes": "secret leak", "adversarial_signal": "secret_leak", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-secret", "content_digest": "password=secret123"}},
    {"bundle_id": "pub-ext-out-of-scope-live", "notes": "publish now", "adversarial_signal": "out_of_scope_live", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-out-of-scope", "content_digest": "publish now"}},
    {"bundle_id": "pub-ext-valid-withdrawal", "notes": "valid withdrawal path", "release_request": {**_BASE_VALID, "request_id": "pub-ext-req-valid-withdrawal"}},
)


def load_pub_ext_fixtures() -> tuple[dict[str, Any], ...]:
    return PUB_EXT_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "PAST_EXPIRY", "PUB_EXT_FIXTURE_BUNDLES", "load_pub_ext_fixtures"]
