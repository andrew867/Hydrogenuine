"""AID disclosure assembly and validation — read-only, no permission."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_core.policy_safety.config import aid_require_evidence_for_capability
from hg_core.policy_safety.errors import REFUSED_HIDE_AI_STATUS, REFUSED_UNPROVEN_CAPABILITY, PolicyValidationError
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.ai_interaction_disclosure.types import InteractionDisclosure, RuntimeMode

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def validate_capability_claim(
    *,
    capability_claim: str,
    evidence_ref: Optional[str],
) -> dict[str, object]:
    """Capability claims require gate/report evidence or render as unproven."""
    if not capability_claim.strip():
        return {**advisory_only_marker(), "status": "no_claim"}
    if aid_require_evidence_for_capability() and not (evidence_ref and evidence_ref.strip()):
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNPROVEN_CAPABILITY,
            "detail": "capability claim lacks evidence ref",
        }
    return {
        **advisory_only_marker(),
        "status": "evidence_linked",
        "evidence_ref": evidence_ref,
    }


def build_disclosure_card(fixture: Mapping[str, str], *, observed_at: str | None = None) -> InteractionDisclosure:
    """Build disclosure card from static fixture state (first safe slice)."""
    if fixture.get("hide_ai", "").lower() == "true":
        raise PolicyValidationError(REFUSED_HIDE_AI_STATUS, "cannot hide AI interaction status")

    capability = fixture.get("capability_claim", "")
    evidence_ref = fixture.get("capability_evidence_ref") or None
    claim_result = validate_capability_claim(capability_claim=capability, evidence_ref=evidence_ref)
    if claim_result.get("status") == "refused":
        raise PolicyValidationError(str(claim_result["reason_code"]), str(claim_result["detail"]))

    runtime_mode: RuntimeMode = fixture.get("runtime_mode", "proposal_only")  # type: ignore[assignment]
    proposal_only = runtime_mode == "proposal_only" or fixture.get("proposal_only", "true").lower() == "true"
    external_action = "disabled" if proposal_only else fixture.get("external_action_status", "disabled")  # type: ignore[assignment]

    return InteractionDisclosure(
        disclosure_id=fixture["disclosure_id"],
        is_ai_interaction=True,
        model_or_provider_label=fixture.get("model_or_provider_label", "unproven"),
        runtime_mode=runtime_mode,
        proposal_only_status=proposal_only,
        authority_boundary="model_proposes_authority_disposes",
        external_action_status=external_action,  # type: ignore[arg-type]
        content_generated_status=fixture.get("content_generated_status", "none"),  # type: ignore[arg-type]
        uncertainty_summary=fixture.get("uncertainty_summary", "fixture_slice"),
        known_limitations=tuple(fixture.get("known_limitations", "offline_fixture").split("|")),
        operator_controls_available=fixture.get("operator_controls", "true").lower() == "true",
        human_review_required=fixture.get("human_review_required", "false").lower() == "true",
        capability_evidence_ref=evidence_ref,
        created_at=observed_at or FIXTURE_CLOCK,
    )


def detect_missing_disclosure(*, interaction_id: str, disclosure: InteractionDisclosure | None) -> dict[str, object]:
    if disclosure is None:
        return {
            **advisory_only_marker(),
            "missing": True,
            "interaction_id": interaction_id,
            "detail": "AID_DISCLOSURE_MISSING_DETECTED",
        }
    return {**advisory_only_marker(), "missing": False, "interaction_id": interaction_id}


__all__ = [
    "FIXTURE_CLOCK",
    "build_disclosure_card",
    "detect_missing_disclosure",
    "validate_capability_claim",
]
