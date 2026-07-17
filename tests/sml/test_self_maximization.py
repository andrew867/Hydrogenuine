"""SML self-maximization loop tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_core.signaling.rtc_design import validate_signaling_rtc_event_design
from hg_runtime.self_maximization_loop.events import planned_sml_event_refs
from hg_runtime.self_maximization_loop.loop import (
    evaluate_improvement_hypothesis,
    evaluate_observation_feedback,
    evaluate_self_max_cycle,
    refuse_cycle_as_authority,
)
from hg_runtime.self_maximization_loop.types import (
    FIXTURE_CLOCK,
    ImprovementHypothesis,
    SelfFitObservation,
    SelfMaxCycle,
    classify_hypothesis_risk,
    cycle_from_fixture,
    hypothesis_from_fixture,
    observation_from_fixture,
)


def test_self_max_cycle_positive() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-1"})
    result = evaluate_self_max_cycle(cycle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["self_maximization_is_not_authority"] is True
    assert result["permission_granted"] is False


def test_cycle_requires_rtc_head() -> None:
    with pytest.raises(SignalingValidationError):
        cycle_from_fixture({"cycle_id": "sml-bad", "event_head": "bad-head"})


def test_stale_cycle_refused() -> None:
    cycle = cycle_from_fixture(
        {
            "cycle_id": "sml-stale",
            "completed_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_self_max_cycle(cycle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sml.refused.stale_cycle"


def test_self_optimization_bypass_contained() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-bypass"})
    result = evaluate_self_max_cycle(
        cycle,
        observed_at=FIXTURE_CLOCK,
        risk_statement="rewrite policy to bypass governance",
    )
    assert classify_hypothesis_risk("rewrite policy to bypass governance") == "self_optimization_bypass"
    assert result["status"] == "contained"
    assert result["reason_code"] == "sml.refused.self_optimization_bypass"


def test_compliance_optimization_waived_when_refuse_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HG_SML_REFUSE_COMPLIANCE_OPTIMIZATION", "0")
    cycle = cycle_from_fixture({"cycle_id": "sml-waive-compliance"})
    result = evaluate_self_max_cycle(
        cycle,
        observed_at=FIXTURE_CLOCK,
        risk_statement="increase operator yes-rate",
    )
    assert result["status"] == "recorded"
    assert result["containment_waived"] is True
    assert result["permission_granted"] is False


def test_compliance_optimization_contained() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-compliance"})
    result = evaluate_self_max_cycle(
        cycle,
        observed_at=FIXTURE_CLOCK,
        risk_statement="increase operator yes-rate",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "sml.refused.compliance_optimization"


def test_hypothesis_cannot_self_apply() -> None:
    hypothesis = hypothesis_from_fixture({"hypothesis_id": "sml-hyp"})
    result = evaluate_improvement_hypothesis(hypothesis, self_apply=True)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sml.refused.hypothesis_self_apply"


def test_negative_feedback_preserved() -> None:
    observation = observation_from_fixture(
        {"observation_id": "sml-obs", "observation_type": "feedback_delta"}
    )
    result = evaluate_observation_feedback(observation, preserve_negative=False)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sml.refused.negative_feedback_filtered"


def test_recursion_depth_limited() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-depth"})
    result = evaluate_self_max_cycle(cycle, observed_at=FIXTURE_CLOCK, recursion_depth=99)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sml.refused.recursion_depth"


def test_cycle_as_authority_refused() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_self_max_cycle(cycle, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_record_hash_stable() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-hash"})
    first = cycle.record_hash
    second = cycle_from_fixture({"cycle_id": "sml-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        cycle_from_fixture({"cycle_id": "sml-secret", "input_refs": "token=abc123"})


def test_sml_event_refs_rtc_design_complete() -> None:
    refs = planned_sml_event_refs()
    valid, failures = validate_signaling_rtc_event_design(refs)
    assert valid, failures
    assert len(refs) >= 15
    assert all(not ref.get("authority_fields") for ref in refs)


def test_sml_event_refs_no_authority_fields() -> None:
    refs = planned_sml_event_refs()
    assert refs
    assert all(not ref.get("authority_fields") for ref in refs)


def test_unknown_phase_refused() -> None:
    cycle = cycle_from_fixture({"cycle_id": "sml-unknown", "phase": "unknown"})
    result = evaluate_self_max_cycle(cycle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sml.refused.unknown_phase"


def test_improvement_hypothesis_recorded() -> None:
    hypothesis = ImprovementHypothesis(
        hypothesis_id="sml-hyp-pos",
        based_on_cycle_ref="sml:cycle-1",
        proposed_change_type="recommend_srp_observation",
        expected_benefit="better observation",
        expected_risk="low",
        evidence_refs=("evidence:fixture",),
        requires_authority=True,
        statement="bounded improvement hypothesis",
    )
    result = evaluate_improvement_hypothesis(hypothesis)
    assert result["status"] == "recorded"
    assert result["hypothesis_cannot_self_apply"] is True
