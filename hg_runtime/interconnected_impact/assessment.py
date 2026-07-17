"""IIL impact assessment evaluation — impact is not permission."""

from __future__ import annotations

from hg_core.developmental.config import iil_fail_closed_physical_blast, iil_refuse_unknown_blast_radius
from hg_core.developmental.errors import (
    REFUSED_IMPACT_AS_PERMISSION,
    REFUSED_IRREVERSIBLE_IMPACT,
    REFUSED_LOCAL_SUCCESS_EXTERNALITY,
    REFUSED_PHYSICAL_BLAST_RADIUS,
    REFUSED_UNKNOWN_BLAST_RADIUS,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.interconnected_impact.types import (
    DownstreamEffect,
    ImpactAssessment,
    assessment_from_fixture,
    detects_local_success_externality,
    effect_from_fixture,
)

_PHYSICAL_BLAST = frozenset({"physical_device", "public_world"})


def refuse_impact_as_permission(*, treat_as_permission: bool) -> None:
    if treat_as_permission:
        raise DevelopmentalValidationError(
            REFUSED_IMPACT_AS_PERMISSION,
            "impact score or assessment cannot become permission",
        )


def evaluate_impact_assessment(
    assessment: ImpactAssessment,
    *,
    treat_as_permission: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_impact_as_permission(treat_as_permission=True)
    if iil_refuse_unknown_blast_radius() and assessment.blast_radius == "unknown":
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_UNKNOWN_BLAST_RADIUS,
            "impact_id": assessment.impact_id,
            "impact_is_not_permission": True,
        }
    if iil_fail_closed_physical_blast() and assessment.blast_radius in _PHYSICAL_BLAST:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_PHYSICAL_BLAST_RADIUS,
            "impact_id": assessment.impact_id,
            "operator_review_recommended": True,
            "impact_is_not_permission": True,
        }
    if assessment.reversibility == "irreversible":
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_IRREVERSIBLE_IMPACT,
            "impact_id": assessment.impact_id,
            "operator_review_recommended": True,
            "impact_is_not_permission": True,
        }
    if detects_local_success_externality(assessment.action_summary):
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_LOCAL_SUCCESS_EXTERNALITY,
            "impact_id": assessment.impact_id,
            "impact_is_not_permission": True,
        }
    if "secrets" in assessment.affected_domains or "privacy" in assessment.affected_domains:
        if assessment.externality_score > 0.5 and not assessment.evidence_refs:
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": "iil.refused.missing_evidence",
                "impact_id": assessment.impact_id,
                "impact_is_not_permission": True,
            }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "iil.advisory.impact_assessment_recorded",
        "impact_id": assessment.impact_id,
        "blast_radius": assessment.blast_radius,
        "impact_is_not_permission": True,
        "local_success_is_not_harmlessness": True,
    }


def evaluate_downstream_effect(
    effect: DownstreamEffect,
    *,
    treat_as_permission: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_impact_as_permission(treat_as_permission=True)
    if effect.effect_type == "irreversible" or effect.severity in {"high", "critical"}:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_IRREVERSIBLE_IMPACT,
            "effect_id": effect.effect_id,
            "impact_is_not_permission": True,
        }
    if effect.effect_type == "cascading":
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": "iil.advisory.cascading_effect_recorded",
            "effect_id": effect.effect_id,
            "operator_review_recommended": True,
            "impact_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "iil.advisory.downstream_effect_recorded",
        "effect_id": effect.effect_id,
        "impact_is_not_permission": True,
    }


def evaluate_assessment_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_impact_assessment(assessment_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_effect_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_downstream_effect(effect_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_assessment_fixture",
    "evaluate_downstream_effect",
    "evaluate_effect_fixture",
    "evaluate_impact_assessment",
    "refuse_impact_as_permission",
]
