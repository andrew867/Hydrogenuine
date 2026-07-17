"""AID policy — capability limits and disclosure evaluation, no permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from hg_core.policy_safety.config import aid_require_evidence_for_capability
from hg_core.policy_safety.errors import REFUSED_POLICY, REFUSED_UNPROVEN_CAPABILITY, PolicyValidationError
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.ai_interaction_disclosure.disclosure import validate_capability_claim
from hg_runtime.ai_interaction_disclosure.types import AID_SCHEMA_VERSION, InteractionDisclosure


@dataclass(frozen=True)
class CapabilityLimitCard:
    limit_card_id: str
    interaction_id: str
    capability_claim: str
    evidence_ref: Optional[str]
    status: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aid-capability-limit-card",
            "schema_version": AID_SCHEMA_VERSION,
            "limit_card_id": self.limit_card_id,
            "interaction_id": self.interaction_id,
            "capability_claim": self.capability_claim,
            "evidence_ref": self.evidence_ref,
            "status": self.status,
            "created_at": self.created_at,
            "card_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def evaluate_capability_limit(
    *,
    interaction_id: str,
    capability_claim: str,
    evidence_ref: Optional[str],
    observed_at: str,
) -> CapabilityLimitCard | dict[str, object]:
    """Evaluate capability claim; refuse unproven claims or return limit card."""
    if not capability_claim.strip():
        return {
            **advisory_only_marker(),
            "status": "no_claim",
            "interaction_id": interaction_id,
        }
    claim_result = validate_capability_claim(capability_claim=capability_claim, evidence_ref=evidence_ref)
    if claim_result.get("status") == "refused":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": claim_result.get("reason_code", REFUSED_UNPROVEN_CAPABILITY),
            "interaction_id": interaction_id,
        }
    return CapabilityLimitCard(
        limit_card_id=f"lim-{interaction_id}",
        interaction_id=interaction_id,
        capability_claim=capability_claim,
        evidence_ref=evidence_ref,
        status="evidence_linked" if evidence_ref else "unproven",
        created_at=observed_at,
    )


def evaluate_disclosure_policy(disclosure: InteractionDisclosure) -> dict[str, object]:
    """Advisory policy check on assembled disclosure — never grants permission."""
    if not disclosure.is_ai_interaction:
        raise PolicyValidationError(REFUSED_POLICY, "AID must disclose AI interaction")
    if aid_require_evidence_for_capability() and disclosure.capability_evidence_ref is None:
        # Empty capability claim is fine; non-empty without evidence is refused at build time
        pass
    return {
        **advisory_only_marker(),
        "status": "advisory_ok",
        "disclosure_id": disclosure.disclosure_id,
        "disclosure_is_not_permission": True,
    }


__all__ = [
    "CapabilityLimitCard",
    "evaluate_capability_limit",
    "evaluate_disclosure_policy",
]
