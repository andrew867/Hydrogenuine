"""Authority-advisory model integration — evidence only, never permission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.model_provider_fabric.types import (
    AuthorityAdvisoryRequest,
    AuthorityAdvisoryResponse,
    ProviderReceipt,
    advisory_envelope,
)

ALLOWED_RECOMMENDATIONS = frozenset({
    "deny",
    "defer",
    "escalate",
    "permit_candidate",
    "review_required",
    "no_change",
})


@dataclass(frozen=True)
class AuthorityAdvisoryReceipt:
    request_id: str
    recommendation: str
    deterministic_gate_state: str
    model_changed_deterministic_outcome: bool
    gpp_permit_present: bool
    permit_expired: bool

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="authority-advisory-receipt",
            request_id=self.request_id,
            recommendation=self.recommendation,
            deterministic_gate_state=self.deterministic_gate_state,
            model_changed_deterministic_outcome=self.model_changed_deterministic_outcome,
            gpp_permit_present=self.gpp_permit_present,
            permit_expired=self.permit_expired,
            rationale_is_non_authority=True,
        )


def deterministic_authority_outcome(
    *,
    gpp_permit_present: bool,
    permit_expired: bool,
    gate_state: str,
) -> str:
    if gate_state == "denied":
        return "deny"
    if not gpp_permit_present:
        return "deny"
    if permit_expired:
        return "deny"
    return "defer"


def authority_advisory_boundary_check(
    request: AuthorityAdvisoryRequest,
    response: AuthorityAdvisoryResponse,
) -> AuthorityAdvisoryReceipt:
    deterministic = deterministic_authority_outcome(
        gpp_permit_present=request.gpp_permit_present,
        permit_expired=request.permit_expired,
        gate_state=request.deterministic_gate_state,
    )
    rec = response.recommendation.lower().strip()
    if rec not in ALLOWED_RECOMMENDATIONS:
        raise ValueError(f"invalid advisory recommendation: {response.recommendation}")
    model_would_grant = rec in {"grant", "approved", "permit_granted", "execute"}
    changed = model_would_grant and deterministic == "deny"
    if changed:
        raise ValueError("model advisory cannot override deterministic deny")
    if not request.gpp_permit_present and rec == "permit_candidate":
        pass  # candidate only — still denies without permit
    return AuthorityAdvisoryReceipt(
        request_id=request.request_id,
        recommendation=rec,
        deterministic_gate_state=request.deterministic_gate_state,
        model_changed_deterministic_outcome=False,
        gpp_permit_present=request.gpp_permit_present,
        permit_expired=request.permit_expired,
    )


def build_advisory_response_from_model_text(request_id: str, text: str) -> AuthorityAdvisoryResponse:
    lower = text.lower()
    if "deny" in lower:
        rec = "deny"
    elif "defer" in lower or "review" in lower:
        rec = "defer"
    elif "escalate" in lower:
        rec = "escalate"
    elif "permit" in lower and "candidate" in lower:
        rec = "permit_candidate"
    else:
        rec = "review_required"
    return AuthorityAdvisoryResponse(
        request_id=request_id,
        recommendation=rec,
        rationale=text[:500],
    )


def provider_receipt_for_advisory(request: AuthorityAdvisoryRequest, response: AuthorityAdvisoryResponse) -> ProviderReceipt:
    return ProviderReceipt(
        receipt_id=f"mpf:auth-advisory:{request.request_id}",
        provider_id="authority-advisory-fabric",
        model_id="advisory-only",
        role="AUTHORITY_ADVISORY",
        organ_id="organ:AuthorityExplanation",
        request_id=request.request_id,
        outcome=response.recommendation,
        fallback_stub=False,
    )


__all__ = [
    "ALLOWED_RECOMMENDATIONS",
    "AuthorityAdvisoryReceipt",
    "authority_advisory_boundary_check",
    "build_advisory_response_from_model_text",
    "deterministic_authority_outcome",
    "provider_receipt_for_advisory",
]
