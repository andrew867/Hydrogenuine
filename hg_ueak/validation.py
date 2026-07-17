"""UEAK admission validation — fail closed; no permit mint."""

from __future__ import annotations

from typing import Optional

from hg_core.governance.capability_registry import lookup_capability
from hg_core.iam.authority import validate_operator_authority
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import STALE_APPROVAL, validate_approval_window
from hg_gpp.store import PermitStore
from hg_gpp.verifier import verify_permit

from hg_ueak.models import ExecutionRefusalReason, ExecutionRequest

DENIED_MISSING_PERMIT = "ueak.denied.missing_permit"
DENIED_MISSING_ADMISSION = "ueak.denied.missing_admission"
DENIED_EXPIRED_PERMIT = "ueak.denied.expired_permit"
DENIED_REVOKED_PERMIT = "ueak.denied.revoked_permit"
DENIED_INVALID_PERMIT = "ueak.denied.invalid_permit"
DENIED_STALE_APPROVAL = "ueak.denied.stale_approval"
DENIED_MISSING_IDENTITY = "ueak.denied.missing_identity"
DENIED_PANIC_LOCKDOWN = "ueak.denied.panic_lockdown"
DENIED_REDACTION_FAILURE = "ueak.denied.redaction_failure"
DENIED_CAPABILITY_MISMATCH = "ueak.denied.capability_mismatch"
DENIED_RETENTION_FAILURE = "ueak.denied.retention_failure"
DENIED_MISSING_ROLLBACK = "ueak.denied.missing_rollback"
DENIED_EMERGENCY_RESTRICT = "ueak.denied.emergency_restrict"
DENIED_RESOURCE_BYPASS = "ueak.denied.resource_bypass"
DENIED_EXPOSURE_INCREASE = "ueak.denied.exposure_increase"
DENIED_FRESHNESS = "ueak.denied.freshness_failure"

_PLACEHOLDER_IDENTITY = frozenset({"", "placeholder", "unknown", "TBD", "operator_id"})


def _is_missing_identity(identity_ref: str) -> bool:
    raw = str(identity_ref or "").strip()
    if raw in _PLACEHOLDER_IDENTITY or raw.startswith("agent:"):
        return True
    return False


def _validate_retention_ref(retention_ref: str) -> bool:
    raw = str(retention_ref or "").strip()
    return bool(raw and raw not in {"ret:missing", "ret:failed", "retention:missing"})


def validate_execution_request(
    request: ExecutionRequest,
    *,
    now: str,
    permit_store: PermitStore,
) -> list[ExecutionRefusalReason]:
    reasons: list[ExecutionRefusalReason] = []

    if request.panic_lockdown:
        reasons.append(ExecutionRefusalReason(DENIED_PANIC_LOCKDOWN, "ADM panic/lockdown active"))

    if request.permit is None:
        if request.risk.resource.pressure_high:
            reasons.append(
                ExecutionRefusalReason(DENIED_RESOURCE_BYPASS, "resource pressure cannot bypass authority")
            )
        reasons.append(ExecutionRefusalReason(DENIED_MISSING_PERMIT, "GPP permit required"))
        return reasons

    permit = request.permit
    chain = request.authority_chain
    if chain.gpp_permit_id and chain.gpp_permit_id != permit.permit_id:
        reasons.append(ExecutionRefusalReason(DENIED_INVALID_PERMIT, "authority chain permit_id mismatch"))
    if chain.gpp_permit_hash and chain.gpp_permit_hash != permit.permit_hash:
        reasons.append(ExecutionRefusalReason(DENIED_INVALID_PERMIT, "authority chain permit_hash mismatch"))

    ok, reason = verify_permit(
        permit,
        now=now,
        store=permit_store,
        action_type=request.candidate.action_type,
        capability_ref=request.candidate.capability_id,
        effect_class=request.candidate.effect_class,
    )
    if not ok:
        code = DENIED_INVALID_PERMIT
        if "expired" in reason:
            code = DENIED_EXPIRED_PERMIT
        elif "revoked" in reason:
            code = DENIED_REVOKED_PERMIT
        elif "scope" in reason:
            code = DENIED_CAPABILITY_MISMATCH
        reasons.append(ExecutionRefusalReason(code, reason))

    if _is_missing_identity(request.identity_ref):
        reasons.append(ExecutionRefusalReason(DENIED_MISSING_IDENTITY, "IAM identity required"))
    elif not validate_operator_authority(request.identity_ref, scope="approve_change", record_event=False).ok:
        reasons.append(ExecutionRefusalReason(DENIED_MISSING_IDENTITY, "IAM authority denied"))

    admission = str(request.admission_ref or "").strip()
    if not admission or admission in {"adm:missing", "admission:missing"}:
        reasons.append(ExecutionRefusalReason(DENIED_MISSING_ADMISSION, "ADM admission required"))

    freshness = str(request.freshness_ref or "").strip()
    if not freshness or freshness in {"tim:missing", "freshness:missing"}:
        reasons.append(ExecutionRefusalReason(DENIED_FRESHNESS, "TIM freshness required"))

    if request.approval_expires_at:
        ok_tim, tim_reason = validate_approval_window(request.approval_expires_at, now)
        if not ok_tim:
            reasons.append(ExecutionRefusalReason(DENIED_STALE_APPROVAL, tim_reason or STALE_APPROVAL))

    redaction = str(request.redaction_ref or "").strip()
    if not redaction or redaction in {"sec:failed", "sec:redaction_failed"}:
        reasons.append(ExecutionRefusalReason(DENIED_REDACTION_FAILURE, "SEC redaction required"))
    elif request.redaction_payload is not None and contains_leak(request.redaction_payload):
        reasons.append(ExecutionRefusalReason(DENIED_REDACTION_FAILURE, "secret leak detected"))

    if not _validate_retention_ref(request.retention_ref):
        reasons.append(ExecutionRefusalReason(DENIED_RETENTION_FAILURE, "RET evidence required"))

    cap = lookup_capability(request.candidate.capability_id)
    if cap is None or not cap.bind_allowed:
        reasons.append(ExecutionRefusalReason(DENIED_CAPABILITY_MISMATCH, "capability denied"))
    elif cap.effect_class != request.candidate.effect_class:
        reasons.append(ExecutionRefusalReason(DENIED_CAPABILITY_MISMATCH, "effect_class mismatch"))

    if request.rollback.required and not str(request.rollback.rollback_ref or "").strip():
        reasons.append(ExecutionRefusalReason(DENIED_MISSING_ROLLBACK, "rollback ref required"))

    emergency = request.risk.emergency
    if emergency.active and emergency.restrict_only:
        if request.candidate.effect_class in {"external_write"} and emergency.mode != "allow_external":
            reasons.append(ExecutionRefusalReason(DENIED_EMERGENCY_RESTRICT, "emergency restrict-only"))

    exposure = request.risk.exposure
    if exposure.is_increase() and not exposure.increase_explicit:
        reasons.append(ExecutionRefusalReason(DENIED_EXPOSURE_INCREASE, "exposure increase not explicit"))

    return reasons


__all__ = [
    "DENIED_CAPABILITY_MISMATCH",
    "DENIED_EMERGENCY_RESTRICT",
    "DENIED_EXPOSURE_INCREASE",
    "DENIED_EXPIRED_PERMIT",
    "DENIED_FRESHNESS",
    "DENIED_INVALID_PERMIT",
    "DENIED_MISSING_ADMISSION",
    "DENIED_MISSING_IDENTITY",
    "DENIED_MISSING_PERMIT",
    "DENIED_MISSING_ROLLBACK",
    "DENIED_PANIC_LOCKDOWN",
    "DENIED_REDACTION_FAILURE",
    "DENIED_RESOURCE_BYPASS",
    "DENIED_RETENTION_FAILURE",
    "DENIED_REVOKED_PERMIT",
    "DENIED_STALE_APPROVAL",
    "validate_execution_request",
]
