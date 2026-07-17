"""SML cycle evaluation — adaptation is not bypass."""

from __future__ import annotations

from hg_core.signaling.config import (
    sml_max_recursion_depth,
    sml_refuse_bypass_hypothesis,
    sml_refuse_compliance_optimization,
    sml_refuse_stale_cycle,
)
from hg_core.signaling.errors import (
    ADVISORY_CONTAINMENT_WAIVED_SML,
    REFUSED_APPEARANCE_MANIPULATION,
    REFUSED_COMPLIANCE_OPTIMIZATION,
    REFUSED_CYCLE_AS_AUTHORITY,
    REFUSED_HYPOTHESIS_SELF_APPLY,
    REFUSED_MISSING_CYCLE_INPUTS,
    REFUSED_NEGATIVE_FEEDBACK_FILTERED,
    REFUSED_RECURSION_DEPTH,
    REFUSED_SELF_OPTIMIZATION_BYPASS,
    REFUSED_STALE_CYCLE,
    REFUSED_UNKNOWN_PHASE,
    SignalingValidationError,
)
from hg_core.signaling.evaluation import resolve_risk_containment
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.self_maximization_loop.types import (
    ImprovementHypothesis,
    SelfFitObservation,
    SelfMaxCycle,
    classify_hypothesis_risk,
    cycle_from_fixture,
    hypothesis_from_fixture,
)

_RISK_REASON = {
    "self_optimization_bypass": REFUSED_SELF_OPTIMIZATION_BYPASS,
    "compliance_optimization": REFUSED_COMPLIANCE_OPTIMIZATION,
    "appearance_manipulation": REFUSED_APPEARANCE_MANIPULATION,
}


def refuse_cycle_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_CYCLE_AS_AUTHORITY,
            "self-maximization cycle or hypothesis cannot become authority",
        )


def evaluate_self_max_cycle(
    cycle: SelfMaxCycle,
    *,
    observed_at: str,
    recursion_depth: int = 0,
    risk_statement: str = "",
    filter_negative_feedback: bool = False,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_cycle_as_authority(treat_as_authority=True)
    if recursion_depth > sml_max_recursion_depth():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_RECURSION_DEPTH,
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        }
    if not cycle.input_refs or not cycle.event_head:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_MISSING_CYCLE_INPUTS,
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        }
    if cycle.phase == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_PHASE,
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        }
    if sml_refuse_stale_cycle() and cycle.completed_at and observed_at > cycle.completed_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_CYCLE,
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        }
    if filter_negative_feedback:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_NEGATIVE_FEEDBACK_FILTERED,
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        }
    risk = classify_hypothesis_risk(risk_statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_SML,
        payload={
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        },
        refuse_for_risk=lambda kind: {
            "compliance_optimization": sml_refuse_compliance_optimization(),
            "self_optimization_bypass": sml_refuse_bypass_hypothesis(),
        }.get(kind, True),
    )
    if contained is not None:
        return contained
    if cycle.phase == "tailor_appearance" and risk == "appearance_manipulation":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_APPEARANCE_MANIPULATION,
            "cycle_id": cycle.cycle_id,
            "self_maximization_is_not_authority": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sml.advisory.cycle_recorded",
        "cycle_id": cycle.cycle_id,
        "phase": cycle.phase,
        "self_maximization_is_not_authority": True,
        "hypothesis_cannot_self_apply": True,
        "feedback_is_not_permission": True,
    }


def evaluate_improvement_hypothesis(
    hypothesis: ImprovementHypothesis,
    *,
    treat_as_authority: bool = False,
    self_apply: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_cycle_as_authority(treat_as_authority=True)
    if self_apply:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_HYPOTHESIS_SELF_APPLY,
            "hypothesis_id": hypothesis.hypothesis_id,
            "hypothesis_cannot_self_apply": True,
        }
    risk = classify_hypothesis_risk(hypothesis.statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_SML,
        payload={
            "hypothesis_id": hypothesis.hypothesis_id,
            "hypothesis_cannot_self_apply": True,
        },
        refuse_for_risk=lambda kind: {
            "compliance_optimization": sml_refuse_compliance_optimization(),
            "self_optimization_bypass": sml_refuse_bypass_hypothesis(),
        }.get(kind, True),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sml.advisory.hypothesis_recorded",
        "hypothesis_id": hypothesis.hypothesis_id,
        "requires_authority": hypothesis.requires_authority,
        "hypothesis_cannot_self_apply": True,
    }


def evaluate_observation_feedback(
    observation: SelfFitObservation,
    *,
    preserve_negative: bool = True,
) -> dict[str, object]:
    if not preserve_negative and observation.observation_type == "feedback_delta":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_NEGATIVE_FEEDBACK_FILTERED,
            "observation_id": observation.observation_id,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sml.advisory.observation_recorded",
        "observation_id": observation.observation_id,
    }


def evaluate_cycle_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_self_max_cycle(
        cycle_from_fixture(fixture),
        risk_statement=str(risk),
        filter_negative_feedback=fixture.get("filter_negative_feedback", "false").lower() == "true",
        **kwargs,  # type: ignore[arg-type]
    )


def evaluate_hypothesis_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_improvement_hypothesis(hypothesis_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_cycle_fixture",
    "evaluate_hypothesis_fixture",
    "evaluate_improvement_hypothesis",
    "evaluate_observation_feedback",
    "evaluate_self_max_cycle",
    "refuse_cycle_as_authority",
]
