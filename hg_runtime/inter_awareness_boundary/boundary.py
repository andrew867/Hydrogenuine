"""IAB inter-awareness evaluation — personalization is not manipulation."""

from __future__ import annotations

from hg_core.developmental.config import iab_refuse_inference_as_consent, iab_refuse_stale_other_model
from hg_core.developmental.errors import (
    REFUSED_FALSE_INTIMACY,
    REFUSED_INFERENCE_AS_CONSENT,
    REFUSED_INFERENCE_AS_TRUTH,
    REFUSED_MANIPULATION_RISK,
    REFUSED_OTHER_MODEL_AS_AUTHORITY,
    REFUSED_STALE_OTHER_MODEL,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.inter_awareness_boundary.types import (
    RelationalClaim,
    ResponseAdaptation,
    adaptation_from_fixture,
    claim_from_fixture,
    classify_relational_risk,
)

_RISK_REASON = {
    "inference_as_consent": REFUSED_INFERENCE_AS_CONSENT,
    "inference_as_truth": REFUSED_INFERENCE_AS_TRUTH,
    "false_intimacy": REFUSED_FALSE_INTIMACY,
    "manipulation_risk": REFUSED_MANIPULATION_RISK,
}


def refuse_other_model_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise DevelopmentalValidationError(
            REFUSED_OTHER_MODEL_AS_AUTHORITY,
            "other-model or relational inference cannot become authority",
        )


def evaluate_relational_claim(
    claim: RelationalClaim,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_other_model_as_authority(treat_as_authority=True)
    if iab_refuse_stale_other_model() and observed_at > claim.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_OTHER_MODEL,
            "claim_id": claim.claim_id,
            "inference_is_not_consent": True,
        }
    risk = classify_relational_risk(claim.claim_text)
    if risk in _RISK_REASON:
        if risk == "inference_as_consent" and not iab_refuse_inference_as_consent():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "claim_id": claim.claim_id,
                "inference_is_not_consent": True,
            }
    if claim.claim_type in {"inferred_need", "consent_claim"} and claim.claim_status != "supported":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_INFERENCE_AS_CONSENT,
            "claim_id": claim.claim_id,
            "inference_is_not_consent": True,
        }
    if claim.claim_status in {"unsupported", "contradicted", "refused"}:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "iab.refused.unsupported_claim",
            "claim_id": claim.claim_id,
            "ask_clarify_recommended": True,
            "inference_is_not_consent": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "iab.advisory.relational_claim_recorded",
        "claim_id": claim.claim_id,
        "inference_is_not_consent": True,
        "personalization_is_not_manipulation": True,
    }


def evaluate_response_adaptation(
    adaptation: ResponseAdaptation,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_other_model_as_authority(treat_as_authority=True)
    if adaptation.manipulation_risk >= 0.7:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_MANIPULATION_RISK,
            "adaptation_id": adaptation.adaptation_id,
            "inference_is_not_consent": True,
        }
    if adaptation.adaptation_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "iab.refused.unknown_adaptation",
            "adaptation_id": adaptation.adaptation_id,
            "inference_is_not_consent": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "iab.advisory.adaptation_recorded",
        "adaptation_id": adaptation.adaptation_id,
        "inference_is_not_consent": True,
    }


def evaluate_claim_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_relational_claim(claim_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_adaptation_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_response_adaptation(adaptation_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_adaptation_fixture",
    "evaluate_claim_fixture",
    "evaluate_relational_claim",
    "evaluate_response_adaptation",
    "refuse_other_model_as_authority",
]
