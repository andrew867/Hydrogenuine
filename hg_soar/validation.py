"""SOAR authority validation — fail closed; no permit mint or execution."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.time.expiry import STALE_APPROVAL, validate_approval_window

from hg_soar.models import SoarBundle, SoarDecisionReason, SoarRequest
from hg_soar.types import DOMAIN_IDS, DomainId

DENIED_MISSING_IDENTITY = "soar.denied.missing_identity"
DENIED_MISSING_ADMISSION = "soar.denied.missing_admission"
DENIED_MISSING_FRESHNESS = "soar.denied.missing_freshness"
DENIED_STALE_APPROVAL = "soar.denied.stale_approval"
DENIED_REDACTION_FAILURE = "soar.denied.redaction_failure"
DENIED_UNKNOWN_DOMAIN = "soar.denied.unknown_domain"
DENIED_DUPLICATE = "soar.denied.duplicate_request"
DENIED_MODEL_AUTHORITY = "soar.denied.model_cannot_authorize"

_PLACEHOLDER_IDENTITY = frozenset({"", "placeholder", "unknown", "TBD", "operator_id"})
_MODEL_PREFIXES = ("model:", "cognition:", "llm:", "srp:auto")


def _is_missing_identity(identity_ref: str) -> bool:
    raw = str(identity_ref or "").strip()
    if raw in _PLACEHOLDER_IDENTITY or raw.startswith("agent:"):
        return True
    lowered = raw.lower()
    return any(lowered.startswith(p) for p in _MODEL_PREFIXES)


def validate_soar_request(
    request: SoarRequest,
    *,
    now: str,
    processed_keys: frozenset[str],
) -> list[SoarDecisionReason]:
    reasons: list[SoarDecisionReason] = []
    idem = request.idempotency_key or request.request_id
    if idem in processed_keys:
        reasons.append(SoarDecisionReason(DENIED_DUPLICATE, "duplicate idempotency key"))

    if _is_missing_identity(request.identity_ref):
        reasons.append(SoarDecisionReason(DENIED_MISSING_IDENTITY, "IAM identity required"))
    elif not validate_operator_authority(request.identity_ref, scope="approve_change", record_event=False).ok:
        reasons.append(SoarDecisionReason(DENIED_MISSING_IDENTITY, "IAM authority denied"))

    admission = str(request.admission_ref or "").strip()
    if not admission or admission in {"adm:missing", "admission:missing"}:
        reasons.append(SoarDecisionReason(DENIED_MISSING_ADMISSION, "ADM admission required"))

    freshness = str(request.freshness_ref or "").strip()
    if not freshness or freshness in {"tim:missing", "freshness:missing"}:
        reasons.append(SoarDecisionReason(DENIED_MISSING_FRESHNESS, "TIM freshness required"))

    if request.approval_expires_at:
        ok, tim_reason = validate_approval_window(request.approval_expires_at, now)
        if not ok:
            reasons.append(SoarDecisionReason(DENIED_STALE_APPROVAL, tim_reason or STALE_APPROVAL))

    redaction = str(request.redaction_ref or "").strip()
    if not redaction or redaction in {"sec:failed", "sec:redaction_failed"}:
        reasons.append(SoarDecisionReason(DENIED_REDACTION_FAILURE, "SEC redaction required"))

    known = set(request.known_domains)
    if known != set(DOMAIN_IDS):
        missing = set(DOMAIN_IDS) - known
        if missing:
            reasons.append(
                SoarDecisionReason(DENIED_UNKNOWN_DOMAIN, f"unknown or missing domains: {sorted(missing)}")
            )

    return reasons


def validate_bundle_domains(bundle: SoarBundle) -> list[SoarDecisionReason]:
    reasons: list[SoarDecisionReason] = []
    seen: set[DomainId] = set()
    for signal in bundle.signals:
        seen.add(signal.domain_id)
        if signal.domain_id != "D7" and not signal.advisory_only:
            reasons.append(
                SoarDecisionReason(DENIED_MODEL_AUTHORITY, f"{signal.domain_id} must be advisory only")
            )
    missing = set(DOMAIN_IDS) - seen
    if missing:
        reasons.append(SoarDecisionReason(DENIED_UNKNOWN_DOMAIN, f"missing domain signals: {sorted(missing)}"))
    return reasons


__all__ = [
    "DENIED_DUPLICATE",
    "DENIED_MISSING_ADMISSION",
    "DENIED_MISSING_FRESHNESS",
    "DENIED_MISSING_IDENTITY",
    "DENIED_MODEL_AUTHORITY",
    "DENIED_REDACTION_FAILURE",
    "DENIED_STALE_APPROVAL",
    "DENIED_UNKNOWN_DOMAIN",
    "validate_bundle_domains",
    "validate_soar_request",
]
