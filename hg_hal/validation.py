"""HAL authority validation — fail closed; no permit mint or execution."""

from __future__ import annotations

from typing import Optional

from hg_core.iam.authority import validate_operator_authority
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import STALE_APPROVAL, validate_approval_window

from hg_hal.models import HalDecisionReason, HalRequest

DENIED_MISSING_IDENTITY = "hal.denied.missing_identity"
DENIED_MISSING_ADMISSION = "hal.denied.missing_admission"
DENIED_MISSING_FRESHNESS = "hal.denied.missing_freshness"
DENIED_STALE_APPROVAL = "hal.denied.stale_approval"
DENIED_REDACTION_FAILURE = "hal.denied.redaction_failure"
DENIED_PANIC_ACTIVE = "hal.denied.panic_active"
DENIED_DEGRADED_ROUTE = "hal.denied.degraded_blocks_route"
DENIED_DUPLICATE = "hal.denied.duplicate_request"
DENIED_AUTHORITY_UNKNOWN = "hal.denied.authority_unknown"
DENIED_UEAK_DIRECT = "hal.denied.ueak_direct_route_forbidden"

_PLACEHOLDER_IDENTITY = frozenset({"", "placeholder", "unknown", "TBD", "operator_id"})
_MODEL_PREFIXES = ("model:", "cognition:", "llm:", "srp:auto")


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


def validate_hal_request(
    request: HalRequest,
    *,
    now: str,
    panic_active: bool,
    degraded_mode: str,
) -> list[HalDecisionReason]:
    reasons: list[HalDecisionReason] = []

    if panic_active:
        reasons.append(HalDecisionReason(DENIED_PANIC_ACTIVE, "panic blocks forward routing"))

    if _is_missing_identity(request.identity_ref):
        reasons.append(HalDecisionReason(DENIED_MISSING_IDENTITY, "IAM identity required"))

    if not _is_missing_identity(request.identity_ref):
        auth = validate_operator_authority(request.identity_ref, scope="approve_change", record_event=False)
        if not auth.ok:
            reasons.append(HalDecisionReason(DENIED_MISSING_IDENTITY, auth.reason_code))

    admission = str(request.admission_ref or "").strip()
    if not admission or admission in {"adm:missing", "admission:missing"}:
        reasons.append(HalDecisionReason(DENIED_MISSING_ADMISSION, "ADM admission required"))

    freshness = str(request.freshness_ref or "").strip()
    if not freshness or freshness in {"tim:missing", "freshness:missing"}:
        reasons.append(HalDecisionReason(DENIED_MISSING_FRESHNESS, "TIM freshness required"))

    if request.approval_expires_at:
        ok, reason = validate_approval_window(request.approval_expires_at, now)
        if not ok:
            reasons.append(HalDecisionReason(DENIED_STALE_APPROVAL, reason or STALE_APPROVAL))
    elif freshness.endswith("stale") or freshness == "tim:stale":
        reasons.append(HalDecisionReason(DENIED_STALE_APPROVAL, STALE_APPROVAL))

    redaction = str(request.redaction_ref or "").strip()
    if not redaction or redaction in {"sec:failed", "sec:redaction_failed"}:
        reasons.append(HalDecisionReason(DENIED_REDACTION_FAILURE, "SEC redaction evidence required"))
    elif request.redaction_payload is not None and contains_leak(request.redaction_payload):
        reasons.append(HalDecisionReason(DENIED_REDACTION_FAILURE, "SEC redaction failure"))

    if degraded_mode not in {"none", ""} and degraded_mode != "operator_only":
        reasons.append(HalDecisionReason(DENIED_AUTHORITY_UNKNOWN, f"unknown degraded mode {degraded_mode!r}"))

    return reasons


__all__ = [
    "DENIED_AUTHORITY_UNKNOWN",
    "DENIED_DEGRADED_ROUTE",
    "DENIED_DUPLICATE",
    "DENIED_MISSING_ADMISSION",
    "DENIED_MISSING_FRESHNESS",
    "DENIED_MISSING_IDENTITY",
    "DENIED_PANIC_ACTIVE",
    "DENIED_REDACTION_FAILURE",
    "DENIED_STALE_APPROVAL",
    "DENIED_UEAK_DIRECT",
    "validate_hal_request",
]
