"""IIL interconnected impact layer tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.interconnected_impact.assessment import (
    evaluate_downstream_effect,
    evaluate_impact_assessment,
    refuse_impact_as_permission,
)
from hg_runtime.interconnected_impact.events import planned_iil_event_refs
from hg_runtime.interconnected_impact.types import (
    DownstreamEffect,
    ImpactAssessment,
    assessment_from_fixture,
    detects_local_success_externality,
    effect_from_fixture,
)


def test_impact_assessment_positive() -> None:
    assessment = assessment_from_fixture({"impact_id": "iil-1", "evidence_refs": "evidence:impact"})
    result = evaluate_impact_assessment(assessment)
    assert result["status"] == "recorded"
    assert result["impact_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_unknown_blast_radius_guarded() -> None:
    assessment = assessment_from_fixture({"impact_id": "iil-unk", "blast_radius": "unknown"})
    result = evaluate_impact_assessment(assessment)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "iil.refused.unknown_blast_radius"


def test_physical_blast_radius_refused() -> None:
    assessment = assessment_from_fixture({"impact_id": "iil-phys", "blast_radius": "public_world"})
    result = evaluate_impact_assessment(assessment)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iil.refused.physical_blast_radius"


def test_irreversible_impact_guarded() -> None:
    assessment = assessment_from_fixture({"impact_id": "iil-irr", "reversibility": "irreversible"})
    result = evaluate_impact_assessment(assessment)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "iil.refused.irreversible_impact"


def test_local_success_externality_contained() -> None:
    summary = "tests passed but logs leak a secret"
    assert detects_local_success_externality(summary)
    assessment = assessment_from_fixture({"impact_id": "iil-loc", "action_summary": summary})
    result = evaluate_impact_assessment(assessment)
    assert result["status"] == "contained"
    assert result["reason_code"] == "iil.refused.local_success_externality"


def test_privacy_missing_evidence_refused() -> None:
    assessment = assessment_from_fixture(
        {
            "impact_id": "iil-privacy",
            "affected_domains": "privacy,secrets",
            "externality_score": "0.8",
            "evidence_refs": "",
        }
    )
    result = evaluate_impact_assessment(assessment)
    assert result["status"] == "refused"
    assert result["reason_code"] == "iil.refused.missing_evidence"


def test_cascading_effect_recorded() -> None:
    effect = effect_from_fixture({"effect_id": "eff-cascade", "effect_type": "cascading"})
    result = evaluate_downstream_effect(effect)
    assert result["reason_code"] == "iil.advisory.cascading_effect_recorded"
    assert result["operator_review_recommended"] is True


def test_impact_as_permission_refused() -> None:
    assessment = assessment_from_fixture({"impact_id": "iil-perm"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_impact_assessment(assessment, treat_as_permission=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_impact_as_permission(treat_as_permission=True)


def test_record_hash_stable() -> None:
    a = assessment_from_fixture({"impact_id": "stable"})
    b = assessment_from_fixture({"impact_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        ImpactAssessment(
            impact_id="bad",
            source_ref="src:fixture",
            source_type="proposed_action",
            actor_id="agent0",
            action_summary="token=secret",
            affected_domains=("runtime_state",),
            blast_radius="local_runtime",
            reversibility="reversible",
            externality_score=0.1,
            uncertainty_score=0.1,
            evidence_refs=(),
        )


def test_iil_event_refs_no_authority_fields() -> None:
    refs = planned_iil_event_refs()
    assert len(refs) >= 14
    assert all(not e.get("authority_fields") for e in refs)


def test_irreversible_downstream_effect_guarded() -> None:
    effect = effect_from_fixture(
        {
            "effect_id": "eff-irr",
            "effect_type": "irreversible",
            "severity": "critical",
        }
    )
    result = evaluate_downstream_effect(effect)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "iil.refused.irreversible_impact"
