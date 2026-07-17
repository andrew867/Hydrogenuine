"""Phase 36 proposal specificity and grounding tests."""

from __future__ import annotations

from hg_runtime.autonomous_proposal_soak.proposal_schema import (
    LOW_SPECIFICITY_STATUS,
    evaluate_organ_output,
    repair_proposal,
    reviewer_sharpening_result,
    route_for_sharpening,
    score_proposal,
)


def _specific_payload(**overrides):
    payload = {
        "proposal_id": "SPECIFIC_REPAIR",
        "title": "finish_reason missing from organ task result",
        "severity": "HIGH",
        "phase_or_component": "Phase 33.6 local_inference_organs",
        "observed_failure": "test organ_task_result_records_finish_reason fails when finish_reason is omitted",
        "reproduction_steps": ["python -m pytest tests/autonomous_agent/test_phase33_6_local_multi_organ_inference_bus.py -q"],
        "expected_behavior": "bus.py includes finish_reason in the organ task result envelope",
        "actual_behavior": "finish_reason is absent from the result envelope",
        "evidence_refs": ["docs/proofs/autonomous_agent_zero/PHASE-33-6/receipt_chain.json"],
        "affected_files": ["hg_runtime/local_inference_organs/bus.py"],
        "affected_tests": ["tests/autonomous_agent/test_phase33_6_local_multi_organ_inference_bus.py::organ_task_result_records_finish_reason"],
        "affected_commands": ["python -m pytest tests/autonomous_agent/test_phase33_6_local_multi_organ_inference_bus.py -q"],
        "authority_risk": "LOW",
        "external_side_effect_risk": "NONE_LOCAL_ONLY",
        "likely_root_cause": "Result serialization drops provider metadata.",
        "acceptance_criteria": ["pytest test organ_task_result_records_finish_reason passes"],
        "finish_reason": "stop",
        "truncated": False,
        "advisory_marker_present": True,
    }
    payload.update(overrides)
    return payload


def _generic_payload(text: str):
    return _specific_payload(
        observed_failure=text,
        reproduction_steps=["UNKNOWN"],
        evidence_refs=[],
        affected_files=["UNKNOWN"],
        affected_tests=["UNKNOWN"],
        affected_commands=["UNKNOWN"],
        acceptance_criteria=[],
    )


def test_generic_review_code_output_is_not_ready():
    assert score_proposal(_generic_payload("Review the code."))["ready_for_spec_tests_plans"] is False


def test_generic_check_dependencies_output_is_not_ready():
    assert score_proposal(_generic_payload("Check dependencies."))["ready_for_spec_tests_plans"] is False


def test_generic_update_software_output_is_not_ready():
    assert score_proposal(_generic_payload("Update software."))["ready_for_spec_tests_plans"] is False


def test_specific_output_with_file_test_command_is_ready():
    scored = score_proposal(_specific_payload())
    assert scored["ready_for_spec_tests_plans"] is True
    assert scored["specificity_score"] >= 8


def test_proposal_requires_evidence_refs_for_ready():
    assert score_proposal(_specific_payload(evidence_refs=[]))["ready_for_spec_tests_plans"] is False


def test_proposal_requires_reproduction_steps_for_ready():
    assert score_proposal(_specific_payload(reproduction_steps=["UNKNOWN"]))["ready_for_spec_tests_plans"] is False


def test_proposal_requires_testable_acceptance_criteria():
    assert score_proposal(_specific_payload(acceptance_criteria=["Looks better."]))["ready_for_spec_tests_plans"] is False


def test_unknown_fields_allowed_but_not_ready():
    scored = score_proposal(_specific_payload(affected_files=["UNKNOWN"], affected_tests=["UNKNOWN"]))
    assert scored["grounding_status"] != "UNGROUNDED"
    assert scored["ready_for_spec_tests_plans"] is False


def test_finish_reason_length_marks_truncated():
    assert score_proposal(_specific_payload(finish_reason="length"))["truncated"] is True


def test_truncated_output_not_ready():
    assert score_proposal(_specific_payload(truncated=True))["ready_for_spec_tests_plans"] is False


def test_missing_advisory_marker_not_green():
    assert score_proposal(_specific_payload(advisory_marker_present=False))["ready_for_spec_tests_plans"] is False


def test_tiny_router_generic_output_routes_to_reviewer():
    route = route_for_sharpening(_generic_payload("Review the code and check dependencies."))
    assert route["route"] == "small_code_reviewer"


def test_reviewer_can_sharpen_generic_output():
    result = reviewer_sharpening_result(_generic_payload("Review the code."), reviewer_output=_specific_payload())
    assert result["sharpened"] is True


def test_reviewer_failure_preserves_low_specificity_proposal():
    result = reviewer_sharpening_result(_generic_payload("Review the code."), reviewer_output=None)
    assert result["status"] == LOW_SPECIFICITY_STATUS
    assert result["ready_for_spec_tests_plans"] is False


def test_small_doc_writer_emits_structured_yaml():
    proposal = repair_proposal(
        {
            "proposal_id": "P33_6_SMALL_DOC_WRITER_LOAD_PATH_LIMITED",
            "title": "small_doc_writer role could not complete under max_loaded_models policy",
            "severity": "HIGH",
            "phase_or_component": "Phase 33.6 local_inference_organs",
            "observed_failure": "P33.6 gate returned YELLOW_LOCAL_MULTI_ORGAN_PARTIAL_LOAD_LIMITED",
            "expected_behavior": "small_doc_writer reuses a compatible loaded tiny model",
            "actual_behavior": "small_doc_writer load path was limited/refused",
            "authority_risk": "LOW",
            "required_tests": ["small_doc_writer_can_reuse_loaded_tiny_model_under_max_loaded_three"],
        },
        evidence_refs=["proof/receipt_chain.json"],
    )
    for field in (
        "affected_files",
        "affected_tests",
        "affected_commands",
        "specificity_score",
        "genericity_score",
        "grounding_status",
        "ready_for_spec_tests_plans",
    ):
        assert field in proposal


def test_specificity_score_deterministic():
    assert score_proposal(_specific_payload())["specificity_score"] == score_proposal(_specific_payload())["specificity_score"]


def test_genericity_score_deterministic():
    assert score_proposal(_generic_payload("Review the code."))["genericity_score"] == score_proposal(_generic_payload("Review the code."))["genericity_score"]


def test_fake_green_generic_proposal_rejected():
    scored = score_proposal(_generic_payload("Review the code and add logging."))
    assert scored["proposal_readiness_status"] == LOW_SPECIFICITY_STATUS


def test_proposal_output_cannot_grant_authority():
    assert evaluate_organ_output(_specific_payload())["grants_authority"] is False


def test_proposal_output_cannot_authorize_tools():
    assert evaluate_organ_output(_specific_payload())["authorizes_tool"] is False


def test_proposal_output_cannot_create_live_effects():
    assert evaluate_organ_output(_specific_payload())["creates_live_effect"] is False
