"""REB-RESTORE-LIVE fixtures — deterministic reentry restore bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_reentry_restore.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

_BASE_VALID = {
    "restore_kind": "checkpoint",
    "checkpoint_digest": "digest:valid-restore",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "checkpoint_ref": "checkpoint:fixture:valid",
    "continuity_policy_ref": "continuity:policy:fixture",
    "rollback_plan_ref": "rollback:plan:fixture",
    "observed_at": FIXTURE_CLOCK,
}

REB_RESTORE_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {"bundle_id": "reb-restore-valid-restore", "notes": "valid restore", "restore_request": {**_BASE_VALID, "request_id": "reb-req-valid"}},
    {"bundle_id": "reb-restore-missing-operator-approval", "notes": "missing operator", "restore_request": {**_BASE_VALID, "request_id": "reb-req-missing-approval", "operator_ref": None}},
    {"bundle_id": "reb-restore-stale-approval", "notes": "stale approval", "restore_request": {**_BASE_VALID, "request_id": "reb-req-stale", "approval_expires_at": PAST_EXPIRY}},
    {"bundle_id": "reb-restore-missing-iam", "notes": "missing IAM", "restore_request": {**_BASE_VALID, "request_id": "reb-req-missing-iam", "operator_ref": "bob"}},
    {"bundle_id": "reb-restore-missing-tim", "notes": "missing TIM", "restore_request": {**_BASE_VALID, "request_id": "reb-req-missing-tim", "freshness_ref": "tim:missing"}},
    {"bundle_id": "reb-restore-stale-tim", "notes": "stale TIM", "restore_request": {**_BASE_VALID, "request_id": "reb-req-stale-tim", "freshness_ref": "tim:stale"}},
    {"bundle_id": "reb-restore-missing-gpp", "notes": "missing GPP", "restore_request": {**_BASE_VALID, "request_id": "reb-req-missing-gpp", "requires_gpp": True}},
    {"bundle_id": "reb-restore-missing-ueak", "notes": "missing UEAK", "restore_request": {**_BASE_VALID, "request_id": "reb-req-missing-ueak", "requires_ueak": True}},
    {"bundle_id": "reb-restore-revoked-permit", "notes": "revoked permit", "restore_request": {**_BASE_VALID, "request_id": "reb-req-revoked", "gpp_permit_ref": "gpp:revoked:fixture"}},
    {"bundle_id": "reb-restore-stale-memory-claim", "notes": "stale memory", "restore_request": {**_BASE_VALID, "request_id": "reb-req-stale-memory", "stale_memory_ref": "memory:stale:truth"}},
    {"bundle_id": "reb-restore-identity-overclaim", "notes": "identity overclaim", "restore_request": {**_BASE_VALID, "request_id": "reb-req-overclaim", "continuity_claim_ref": "identity:overclaim:fixture"}},
    {"bundle_id": "reb-restore-missing-rollback-plan", "notes": "missing rollback", "restore_request": {**_BASE_VALID, "request_id": "reb-req-missing-rollback", "rollback_plan_ref": None}},
    {"bundle_id": "reb-restore-authority-conversion", "notes": "authority conversion", "adversarial_signal": "authority_conversion", "restore_request": {**_BASE_VALID, "request_id": "reb-req-authority", "treat_as_authority": True}},
    {"bundle_id": "reb-restore-secret-leak", "notes": "secret leak", "adversarial_signal": "secret_leak", "restore_request": {**_BASE_VALID, "request_id": "reb-req-secret", "checkpoint_digest": "password=secret123"}},
    {"bundle_id": "reb-restore-out-of-scope-live", "notes": "restore now", "adversarial_signal": "out_of_scope_live", "restore_request": {**_BASE_VALID, "request_id": "reb-req-out-of-scope", "checkpoint_digest": "restore checkpoint now"}},
    {"bundle_id": "reb-restore-valid-continuity-refusal", "notes": "continuity refusal path", "restore_request": {**_BASE_VALID, "request_id": "reb-req-valid-continuity-refusal", "continuity_claim_ref": "continuity:refusal:fixture"}},
)


def load_reb_restore_fixtures() -> tuple[dict[str, Any], ...]:
    return REB_RESTORE_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "PAST_EXPIRY", "REB_RESTORE_FIXTURE_BUNDLES", "load_reb_restore_fixtures"]
