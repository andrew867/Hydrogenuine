"""AID typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.policy_safety.errors import REFUSED_PROPOSAL_AS_ACTION, PolicyValidationError
from hg_core.policy_safety.hashing import compute_record_hash

AID_SCHEMA_VERSION = "1.0"

RuntimeMode = Literal["offline", "proposal_only", "live_disabled", "unknown"]


@dataclass(frozen=True)
class InteractionDisclosure:
    disclosure_id: str
    is_ai_interaction: bool
    model_or_provider_label: str
    runtime_mode: RuntimeMode
    proposal_only_status: bool
    authority_boundary: str
    external_action_status: Literal["disabled", "enabled", "unknown"]
    content_generated_status: Literal["none", "partial", "present", "unknown"]
    uncertainty_summary: str
    known_limitations: tuple[str, ...]
    operator_controls_available: bool
    human_review_required: bool
    capability_evidence_ref: Optional[str]
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_disclosure(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aid-interaction-disclosure",
            "schema_version": AID_SCHEMA_VERSION,
            "disclosure_id": self.disclosure_id,
            "is_ai_interaction": self.is_ai_interaction,
            "model_or_provider_label": self.model_or_provider_label,
            "runtime_mode": self.runtime_mode,
            "proposal_only_status": self.proposal_only_status,
            "authority_boundary": self.authority_boundary,
            "external_action_status": self.external_action_status,
            "content_generated_status": self.content_generated_status,
            "uncertainty_summary": self.uncertainty_summary,
            "known_limitations": list(self.known_limitations),
            "operator_controls_available": self.operator_controls_available,
            "human_review_required": self.human_review_required,
            "capability_evidence_ref": self.capability_evidence_ref,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_disclosure(card: InteractionDisclosure) -> None:
    if not card.disclosure_id.strip():
        raise PolicyValidationError("aid.validation.disclosure_id", "disclosure_id required")
    if not card.is_ai_interaction:
        raise PolicyValidationError("aid.validation.is_ai_interaction", "AID cards must disclose AI interaction")
    if card.proposal_only_status and card.external_action_status == "enabled":
        raise PolicyValidationError(
            REFUSED_PROPOSAL_AS_ACTION,
            "proposal-only cannot show external action enabled",
        )


__all__ = ["AID_SCHEMA_VERSION", "InteractionDisclosure", "RuntimeMode", "validate_disclosure"]
