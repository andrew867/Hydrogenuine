"""SRP-LIVE pure decision function — plan/apply separation; no authority minting."""

from __future__ import annotations

from typing import Any, Literal

from hg_core.srp_live.config import srp_refuse_self_modification, srp_restrict_only_default
from hg_core.srp_live.errors import (
    APPLY_FAKE,
    FAIL_CLOSED,
    REJECT_BAC_LAUNDERING,
    REJECT_DIGEST_MISMATCH,
    REJECT_EXPIRED_OR_REVOKED,
    REJECT_LIVENESS_DEGRADED,
    REJECT_NAKED_PATCH,
    REJECT_NO_ADMISSION,
    REJECT_NO_PERMIT,
    REJECT_NO_ROLLBACK,
    REJECT_PANIC_LOCKDOWN,
    REJECT_STALE_SANDBOX_PROOF,
    REJECT_UNSIGNED_APPROVAL,
    REFUSED_SELF_MODIFICATION,
    ROUTE_TO_CHANGE_CONTROL,
)

SrpApplyDecision = Literal[
    "APPLY_FAKE",
    "ROUTE_TO_CHANGE_CONTROL",
    "REJECT_NO_PERMIT",
    "REJECT_NO_ADMISSION",
    "REJECT_EXPIRED_OR_REVOKED",
    "REJECT_UNSIGNED_APPROVAL",
    "REJECT_STALE_SANDBOX_PROOF",
    "REJECT_DIGEST_MISMATCH",
    "REJECT_NO_ROLLBACK",
    "REJECT_NAKED_PATCH",
    "REJECT_BAC_LAUNDERING",
    "REJECT_LIVENESS_DEGRADED",
    "REJECT_PANIC_LOCKDOWN",
    "FAIL_CLOSED",
]


def srp_apply_decide(
    *,
    request: dict[str, Any],
    permit_binding: dict[str, Any] | None = None,
    admission_token: dict[str, Any] | None = None,
    change_control_state: dict[str, Any] | None = None,
    boundary_liveness_state: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Pure decision over fixture inputs; returns exactly one outcome."""
    req = request or {}
    permit = permit_binding or {}
    admission = admission_token or {}
    cc = change_control_state or {}
    boundary = boundary_liveness_state or {}

    if boundary.get("panic_lockdown") is True:
        return _decision(REJECT_PANIC_LOCKDOWN, request_id=req.get("repair_id"))

    if boundary.get("liveness_degraded") is True:
        return _decision(REJECT_LIVENESS_DEGRADED, request_id=req.get("repair_id"))

    if srp_refuse_self_modification() and req.get("self_approved") is True:
        return _decision(REFUSED_SELF_MODIFICATION, request_id=req.get("repair_id"))

    if req.get("treat_as_authority") is True:
        return _decision("FAIL_CLOSED", request_id=req.get("repair_id"), reason_code=FAIL_CLOSED)

    if cc.get("approval_missing") is True or cc.get("approval_stale") is True:
        return _decision(ROUTE_TO_CHANGE_CONTROL, request_id=req.get("repair_id"))

    if not permit.get("gpp_permit_ref"):
        return _decision(REJECT_NO_PERMIT, request_id=req.get("repair_id"))

    if permit.get("expired") is True or permit.get("revoked") is True:
        return _decision(REJECT_EXPIRED_OR_REVOKED, request_id=req.get("repair_id"))

    if not admission.get("ueak_admission_ref"):
        return _decision(REJECT_NO_ADMISSION, request_id=req.get("repair_id"))

    if cc.get("approval_signed") is not True:
        return _decision(REJECT_UNSIGNED_APPROVAL, request_id=req.get("repair_id"))

    sandbox_ref = req.get("sandbox_proof_ref")
    if not sandbox_ref or cc.get("sandbox_proof_stale") is True:
        return _decision(REJECT_STALE_SANDBOX_PROOF, request_id=req.get("repair_id"))

    approved_digest = req.get("approved_digest")
    request_digest = req.get("change_set_digest")
    if not approved_digest or not request_digest or approved_digest != request_digest:
        return _decision(REJECT_DIGEST_MISMATCH, request_id=req.get("repair_id"))

    if not req.get("tep_envelope_ref"):
        return _decision(REJECT_NAKED_PATCH, request_id=req.get("repair_id"))

    rollback = req.get("rollback_plan_ref")
    if not rollback:
        return _decision(REJECT_NO_ROLLBACK, request_id=req.get("repair_id"))

    if req.get("irreversible_step") is True and cc.get("irreversible_ack") is not True:
        return _decision(REJECT_NO_ROLLBACK, request_id=req.get("repair_id"))

    if cc.get("bac_laundering") is True:
        return _decision(REJECT_BAC_LAUNDERING, request_id=req.get("repair_id"))

    if not srp_restrict_only_default():
        return _decision("FAIL_CLOSED", request_id=req.get("repair_id"), reason_code=FAIL_CLOSED)

    return {
        "decision": APPLY_FAKE,
        "reason_code": APPLY_FAKE,
        "repair_id": req.get("repair_id"),
        "restrict_only": True,
        "srp_apply_called": False,
        "gpp_permit_minted": False,
        "live_landing_performed": False,
        "permission_granted": False,
        "authority_created": False,
    }


def _decision(
    decision: str,
    *,
    request_id: object = None,
    reason_code: str | None = None,
) -> dict[str, object]:
    code = reason_code or decision
    return {
        "decision": decision,
        "reason_code": code,
        "repair_id": request_id,
        "restrict_only": True,
        "srp_apply_called": False,
        "gpp_permit_minted": False,
        "live_landing_performed": False,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["SrpApplyDecision", "srp_apply_decide"]
