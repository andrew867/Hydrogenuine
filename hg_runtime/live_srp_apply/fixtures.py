"""SRP-LIVE fixtures — deterministic SRP apply bundles."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_srp_apply.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

_VALID_DIGEST = "digest:approved-fixture"
_VALID_SANDBOX = "sandbox:proof:fresh"
_VALID_TEP = "tep:envelope:fixture"
_VALID_ROLLBACK = "rollback:plan:fixture"
_VALID_PERMIT = "gpp:permit:fixture"
_VALID_ADMISSION = "ueak:admission:fixture"

_BASE_REQUEST: dict[str, Any] = {
    "repair_id": "srp-repair-valid",
    "target_ref": "target:repo:fixture",
    "change_set_digest": _VALID_DIGEST,
    "approved_digest": _VALID_DIGEST,
    "sandbox_proof_ref": _VALID_SANDBOX,
    "approval_receipt_ref": "approval:receipt:signed",
    "operator_ref": "op:local",
    "freshness_ref": "tim:approval_window_ok",
    "approval_expires_at": FUTURE_EXPIRY,
    "scope": "approve_change",
    "tep_envelope_ref": _VALID_TEP,
    "rollback_plan_ref": _VALID_ROLLBACK,
    "gpp_permit_ref": _VALID_PERMIT,
    "ueak_admission_ref": _VALID_ADMISSION,
    "observed_at": FIXTURE_CLOCK,
}

_BASE_PERMIT_BINDING: dict[str, Any] = {
    "binding_id": "bind:srp-repair-valid",
    "repair_id": "srp-repair-valid",
    "gpp_permit_ref": _VALID_PERMIT,
    "ueak_admission_ref": _VALID_ADMISSION,
}

_BASE_CHANGE_CONTROL: dict[str, Any] = {
    "approval_signed": True,
    "sandbox_proof_stale": False,
    "bac_laundering": False,
}

SRP_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "srp-valid-apply",
        "notes": "valid apply path with plan/apply separation and fake sink",
        "apply_request": dict(_BASE_REQUEST),
        "permit_binding": dict(_BASE_PERMIT_BINDING),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-missing-permit",
        "notes": "missing GPP permit → REJECT_NO_PERMIT",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-no-permit"),
        "permit_binding": {
            "binding_id": "bind:srp-repair-no-permit",
            "repair_id": "srp-repair-no-permit",
            "gpp_permit_ref": None,
            "ueak_admission_ref": _VALID_ADMISSION,
        },
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-missing-admission",
        "notes": "missing UEAK admission → REJECT_NO_ADMISSION",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-no-admission"),
        "permit_binding": {
            "binding_id": "bind:srp-repair-no-admission",
            "repair_id": "srp-repair-no-admission",
            "gpp_permit_ref": _VALID_PERMIT,
            "ueak_admission_ref": None,
        },
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-expired-permit",
        "notes": "expired permit → REJECT_EXPIRED_OR_REVOKED",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-expired"),
        "permit_binding": {
            "binding_id": "bind:srp-repair-expired",
            "repair_id": "srp-repair-expired",
            "gpp_permit_ref": _VALID_PERMIT,
            "ueak_admission_ref": _VALID_ADMISSION,
            "expired": True,
        },
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-unsigned-approval",
        "notes": "unsigned approval → REJECT_UNSIGNED_APPROVAL",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-unsigned"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-unsigned", binding_id="bind:srp-repair-unsigned"),
        "change_control_state": {"approval_signed": False, "sandbox_proof_stale": False, "bac_laundering": False},
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-stale-sandbox-proof",
        "notes": "stale sandbox proof → REJECT_STALE_SANDBOX_PROOF",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-stale-sandbox"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-stale-sandbox", binding_id="bind:srp-repair-stale-sandbox"),
        "change_control_state": {"approval_signed": True, "sandbox_proof_stale": True, "bac_laundering": False},
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-digest-mismatch",
        "notes": "digest drift → REJECT_DIGEST_MISMATCH",
        "apply_request": dict(
            _BASE_REQUEST,
            repair_id="srp-repair-digest-mismatch",
            change_set_digest="digest:drifted",
            approved_digest=_VALID_DIGEST,
        ),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-digest-mismatch", binding_id="bind:srp-repair-digest-mismatch"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-missing-rollback",
        "notes": "missing rollback plan → REJECT_NO_ROLLBACK",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-no-rollback", rollback_plan_ref=None),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-no-rollback", binding_id="bind:srp-repair-no-rollback"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-naked-patch",
        "notes": "no TEP envelope → REJECT_NAKED_PATCH",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-naked", tep_envelope_ref=None),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-naked", binding_id="bind:srp-repair-naked"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-bac-laundering",
        "notes": "BAC laundering chain → REJECT_BAC_LAUNDERING",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-bac"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-bac", binding_id="bind:srp-repair-bac"),
        "change_control_state": {"approval_signed": True, "sandbox_proof_stale": False, "bac_laundering": True},
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-liveness-degraded",
        "notes": "liveness degraded → REJECT_LIVENESS_DEGRADED",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-liveness"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-liveness", binding_id="bind:srp-repair-liveness"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": True},
    },
    {
        "bundle_id": "srp-panic-lockdown",
        "notes": "panic lockout → REJECT_PANIC_LOCKDOWN",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-panic"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-panic", binding_id="bind:srp-repair-panic"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": True, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-stale-approval-route",
        "notes": "stale human approval → ROUTE_TO_CHANGE_CONTROL",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-stale-approval"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-stale-approval", binding_id="bind:srp-repair-stale-approval"),
        "change_control_state": {"approval_signed": True, "approval_stale": True, "sandbox_proof_stale": False, "bac_laundering": False},
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-self-approval",
        "notes": "self-modification without authority refusal",
        "adversarial_signal": "self_modification",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-self", self_approved=True),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-self", binding_id="bind:srp-repair-self"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-authority-conversion",
        "notes": "authority conversion refusal",
        "adversarial_signal": "authority_conversion",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-auth-conv", treat_as_authority=True),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-auth-conv", binding_id="bind:srp-repair-auth-conv"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-secret-leak",
        "notes": "secret redaction refusal",
        "adversarial_signal": "secret_leak",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-secret", target_ref="password=secret123"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-secret", binding_id="bind:srp-repair-secret"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-valid-rollback",
        "notes": "valid rollback after fake-sink apply",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-rollback"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-rollback", binding_id="bind:srp-repair-rollback"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-missing-iam",
        "notes": "missing IAM refusal",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-missing-iam", operator_ref="bob"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-missing-iam", binding_id="bind:srp-repair-missing-iam"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
    {
        "bundle_id": "srp-missing-tim",
        "notes": "missing TIM freshness refusal",
        "apply_request": dict(_BASE_REQUEST, repair_id="srp-repair-missing-tim", freshness_ref="tim:missing"),
        "permit_binding": dict(_BASE_PERMIT_BINDING, repair_id="srp-repair-missing-tim", binding_id="bind:srp-repair-missing-tim"),
        "change_control_state": dict(_BASE_CHANGE_CONTROL),
        "boundary_liveness_state": {"panic_lockdown": False, "liveness_degraded": False},
    },
)


def load_srp_fixtures() -> tuple[dict[str, Any], ...]:
    return SRP_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "PAST_EXPIRY", "SRP_FIXTURE_BUNDLES", "load_srp_fixtures"]
