"""GPP permit validation — IAM/ADM/TIM/SEC/RET/evidence checks only."""

from __future__ import annotations

from typing import Any, Optional

from hg_core.governance.capability_registry import lookup_capability, lookup_decision
from hg_core.iam.authority import validate_operator_authority
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import STALE_APPROVAL, validate_approval_window

from hg_gpp.models import PermitDenyReason, PermitRequest

DENIED_MISSING_IDENTITY = "gpp.denied.missing_identity"
DENIED_STALE_APPROVAL = "gpp.denied.stale_approval"
DENIED_MISSING_ADMISSION = "gpp.denied.missing_admission"
DENIED_MISSING_FRESHNESS = "gpp.denied.missing_freshness"
DENIED_REDACTION_FAILURE = "gpp.denied.redaction_failure"
DENIED_RETENTION_FAILURE = "gpp.denied.retention_failure"
DENIED_MISSING_EVIDENCE = "gpp.denied.missing_evidence"
DENIED_MISSING_PROOF = "gpp.denied.missing_proof_refs"
DENIED_CAPABILITY_MISMATCH = "gpp.denied.capability_mismatch"
DENIED_SCOPE_MISMATCH = "gpp.denied.scope_mismatch"
DENIED_DECISION_DENIED = "gpp.denied.decision_denied"
DENIED_SELF_MINT = "gpp.denied.self_mint"
DENIED_UNKNOWN_CAPABILITY = "gpp.denied.unknown_capability"
DENIED_BIND_NOT_ALLOWED = "gpp.denied.bind_not_allowed"

_PLACEHOLDER_IDENTITY = frozenset({"", "placeholder", "unknown", "TBD", "operator_id"})
_MODEL_PREFIXES = ("model:", "cognition:", "llm:", "srp:auto")
_GPP_ISSUER = "gpp:permit_authority"


def _is_missing_identity(identity_ref: str) -> bool:
    raw = str(identity_ref or "").strip()
    if raw in _PLACEHOLDER_IDENTITY:
        return True
    lowered = raw.lower()
    if raw.startswith("agent:") or raw == "agent:zero":
        return True
    if any(lowered.startswith(p) for p in _MODEL_PREFIXES):
        return True
    return False


def _validate_retention_ref(retention_ref: str) -> bool:
    raw = str(retention_ref or "").strip()
    if not raw or raw in {"ret:missing", "ret:failed", "retention:missing"}:
        return False
    if raw.startswith("ret:") and len(raw) > 4:
        return True
    return bool(raw)


def validate_permit_request(
    request: PermitRequest,
    *,
    now: str,
    issuer_id: str = _GPP_ISSUER,
) -> list[PermitDenyReason]:
    """Fail-closed validation before permit mint."""
    reasons: list[PermitDenyReason] = []

    if request.requestor_id == issuer_id:
        reasons.append(PermitDenyReason(DENIED_SELF_MINT, "requestor cannot mint permits"))

    if _is_missing_identity(request.identity_ref):
        reasons.append(PermitDenyReason(DENIED_MISSING_IDENTITY, "IAM identity required"))

    operator = request.operator_ref or request.identity_ref
    if operator and not _is_missing_identity(operator):
        auth = validate_operator_authority(operator, scope="approve_change", record_event=False)
        if not auth.ok and operator == request.identity_ref:
            reasons.append(PermitDenyReason(DENIED_MISSING_IDENTITY, auth.reason_code))

    admission = str(request.admission_ref or "").strip()
    if not admission or admission in {"adm:missing", "admission:missing"}:
        reasons.append(PermitDenyReason(DENIED_MISSING_ADMISSION, "ADM admission token required"))

    freshness = str(request.freshness_ref or "").strip()
    if not freshness or freshness in {"tim:missing", "freshness:missing"}:
        reasons.append(PermitDenyReason(DENIED_MISSING_FRESHNESS, "TIM freshness ref required"))

    if request.approval_expires_at:
        ok, reason = validate_approval_window(request.approval_expires_at, now)
        if not ok:
            reasons.append(PermitDenyReason(DENIED_STALE_APPROVAL, reason or STALE_APPROVAL))
    elif freshness.endswith("stale") or freshness == "tim:stale":
        reasons.append(PermitDenyReason(DENIED_STALE_APPROVAL, STALE_APPROVAL))

    if not request.evidence_refs:
        reasons.append(PermitDenyReason(DENIED_MISSING_EVIDENCE, "evidence_refs required"))

    if not request.proof_bundle_refs:
        reasons.append(PermitDenyReason(DENIED_MISSING_PROOF, "proof_bundle_refs required"))

    redaction = str(request.redaction_ref or "").strip()
    if not redaction or redaction in {"sec:failed", "sec:redaction_failed"}:
        reasons.append(PermitDenyReason(DENIED_REDACTION_FAILURE, "SEC redaction evidence required"))
    elif request.redaction_payload is not None and contains_leak(request.redaction_payload):
        reasons.append(PermitDenyReason(DENIED_REDACTION_FAILURE, "secret leak in redaction payload"))

    if not _validate_retention_ref(request.retention_ref):
        reasons.append(PermitDenyReason(DENIED_RETENTION_FAILURE, "RET retention evidence required"))

    cap = lookup_capability(request.capability_ref)
    if cap is None:
        reasons.append(PermitDenyReason(DENIED_UNKNOWN_CAPABILITY, request.capability_ref))
    elif not cap.bind_allowed:
        reasons.append(PermitDenyReason(DENIED_BIND_NOT_ALLOWED, cap.capability_id))
    elif request.scope.capability_ref != cap.capability_id:
        reasons.append(PermitDenyReason(DENIED_CAPABILITY_MISMATCH, "scope capability mismatch"))
    elif request.scope.effect_class != cap.effect_class:
        reasons.append(PermitDenyReason(DENIED_CAPABILITY_MISMATCH, "effect_class mismatch"))

    decision = lookup_decision(request.authority_chain_ref)
    if decision is None:
        reasons.append(PermitDenyReason(DENIED_DECISION_DENIED, "unknown authority chain ref"))
    elif decision.verdict != "allow":
        reasons.append(PermitDenyReason(DENIED_DECISION_DENIED, decision.reason_code or "denied"))

    if request.scope.capability_ref != request.capability_ref:
        reasons.append(PermitDenyReason(DENIED_SCOPE_MISMATCH, "scope vs capability_ref"))

    return reasons


__all__ = [
    "DENIED_BIND_NOT_ALLOWED",
    "DENIED_CAPABILITY_MISMATCH",
    "DENIED_DECISION_DENIED",
    "DENIED_MISSING_ADMISSION",
    "DENIED_MISSING_EVIDENCE",
    "DENIED_MISSING_FRESHNESS",
    "DENIED_MISSING_IDENTITY",
    "DENIED_MISSING_PROOF",
    "DENIED_REDACTION_FAILURE",
    "DENIED_RETENTION_FAILURE",
    "DENIED_SCOPE_MISMATCH",
    "DENIED_SELF_MINT",
    "DENIED_STALE_APPROVAL",
    "validate_permit_request",
]
