"""Phase 31 generalization-evaluation-harness tests.

The harness measures held-out transfer. It must reject answer-key leakage,
surface similarity, cherry-picked single successes claimed as general competence,
and any path by which an evaluation result grants or widens authority.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.generalization_eval import (
    GeneralizationEvalError,
    GeneralizationEvalLog,
    accept_acquired_mini_task,
    audit_leakage,
    bounded_claim_scope,
    build_claim_scope,
    build_domain_readiness,
    build_generalization_receipt,
    build_generalization_result,
    create_case_split,
    create_rubric,
    define_heldout_case,
    define_transfer_eval_case,
    has_rubric,
    proof_gate_to_fpga_trng_case,
    register_skill_transfer_candidate,
    run_negative_control,
    run_positive_control,
    score_transfer,
)
from hg_runtime.generalization_eval.gate import (
    evaluate_phase31_gate,
    validate_phase31_proof_bundle,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "phase31"
BOUNDARY = "generalization_eval_advisory_default"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _heldout(**overrides):
    payload = {
        "case_id": "ho-1",
        "task": "validate an unseen FPGA TRNG entropy source",
        "expected_behavior": "demand measured entropy before passing",
        "claim_boundary": BOUNDARY,
    }
    payload.update(overrides)
    return payload


def _rubric(**overrides):
    payload = {
        "rubric_id": "rub-1",
        "criteria": ["defines held-out case", "demands evidence", "refuses similarity"],
        "pass_threshold": 2,
    }
    payload.update(overrides)
    return payload


def _passing_leakage_audit():
    return audit_leakage({"audit_id": "la-1", "case_ref": "ho-1", "split_ref": "split-1"})


# --- held-out cases & answer-key exclusion ---------------------------------

def test_heldout_case_cannot_include_answer_key():
    with pytest.raises(GeneralizationEvalError, match="answer_key_leak_rejected"):
        define_heldout_case(_heldout(answer_key="PASS"))


def test_valid_heldout_case_round_trips():
    case = define_heldout_case(_load("valid_heldout_case_v1.json"))
    assert case["schema"] == "heldout_case_v1"
    assert case["held_out"] is True
    assert case["tool_authorized"] is False


def test_invalid_heldout_case_fixture_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="answer_key_leak_rejected"):
        define_heldout_case(_load("invalid_heldout_case_with_answer_key_v1.json"))


def test_nested_answer_key_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="answer_key_leak_rejected"):
        define_heldout_case(_heldout(payload={"solution": "42"}))


# --- surface similarity ----------------------------------------------------

def test_surface_similarity_does_not_score_as_transfer():
    with pytest.raises(GeneralizationEvalError, match="surface_similarity_not_transfer"):
        score_transfer(
            {
                "score_id": "sc-1",
                "case_ref": "ho-1",
                "rubric": _rubric(),
                "met_criteria": ["defines held-out case", "demands evidence"],
                "evidence_refs": ["ev-1"],
            },
            similarity_only=True,
        )


def test_similarity_as_proof_payload_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="surface_similarity_rejected"):
        define_heldout_case(_heldout(similarity_is_proof=True))


# --- controls --------------------------------------------------------------

def test_negative_control_fails_expectedly():
    result = run_negative_control({"control_id": "nc-1", "case_ref": "ho-bias", "observed_outcome": "fail"})
    assert result["passed_as_expected"] is True
    assert result["silent_pass"] is False


def test_negative_control_silent_pass_is_flagged():
    result = run_negative_control({"control_id": "nc-2", "case_ref": "ho-bias", "observed_outcome": "pass"})
    assert result["passed_as_expected"] is False
    assert result["silent_pass"] is True


def test_negative_control_result_is_recorded():
    result = run_negative_control({"control_id": "nc-3", "case_ref": "ho-bias", "observed_outcome": "pass"})
    assert result["recorded"] is True
    assert result["hidden"] is False


def test_positive_control_passes_with_rubric():
    result = run_positive_control(
        {"control_id": "pc-1", "case_ref": "ho-1", "observed_outcome": "pass", "rubric_ref": "rub-1"}
    )
    assert result["passed_as_expected"] is True


def test_positive_control_requires_rubric():
    with pytest.raises(GeneralizationEvalError, match="positive_control_requires_rubric"):
        run_positive_control({"control_id": "pc-2", "case_ref": "ho-1", "observed_outcome": "pass", "rubric_ref": ""})


# --- the canonical proof-gate -> fpga trng case ----------------------------

def test_proof_gate_to_fpga_trng_case_has_rubric():
    case = proof_gate_to_fpga_trng_case()
    assert has_rubric(case) is True
    assert case["rubric"]["criteria"]
    assert case["rubric_ref"] == case["rubric"]["rubric_id"]


# --- leakage audits --------------------------------------------------------

def test_leakage_audit_required_for_heldout_case():
    with pytest.raises(GeneralizationEvalError, match="leakage_audit_required_for_heldout_case"):
        build_generalization_result(
            {
                "result_id": "res-1",
                "case_ref": "ho-1",
                "split_ref": "split-1",
                "status": "passed",
                "evidence_refs": ["ev-1"],
                "receipt_refs": ["rc-1"],
                "claim_boundary": BOUNDARY,
            }
        )


def test_answer_key_leakage_blocks_green():
    leak = audit_leakage(
        {"audit_id": "la-2", "case_ref": "ho-1", "split_ref": "split-1", "case": {"answer_key": "PASS"}}
    )
    assert leak["leak_detected"] is True
    with pytest.raises(GeneralizationEvalError, match="answer_key_leakage_blocks_green"):
        build_generalization_result(
            {
                "result_id": "res-2",
                "case_ref": "ho-1",
                "split_ref": "split-1",
                "status": "passed",
                "evidence_refs": ["ev-1"],
                "receipt_refs": ["rc-1"],
                "leakage_audit": leak,
                "claim_boundary": BOUNDARY,
            }
        )


def test_case_in_training_split_is_a_leak():
    leak = audit_leakage(
        {"audit_id": "la-3", "case_ref": "ho-1", "split_ref": "split-1", "train_refs": ["ho-1", "ho-x"]}
    )
    assert leak["leak_detected"] is True
    assert "case_in_training_split" in leak["reasons"]


# --- splits ----------------------------------------------------------------

def test_case_split_record_required():
    with pytest.raises(GeneralizationEvalError, match="case_split_record_required"):
        build_generalization_result(
            {
                "result_id": "res-3",
                "case_ref": "ho-1",
                "split_ref": "",
                "status": "fail",
                "failure_memory_ref": "mem-1",
                "claim_boundary": BOUNDARY,
            }
        )


def test_case_split_overlap_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="case_split_train_heldout_overlap"):
        create_case_split(_load("invalid_case_split_overlap_v1.json"))


def test_valid_case_split_round_trips():
    split = create_case_split(_load("valid_case_split_record_v1.json"))
    assert split["schema"] == "case_split_record_v1"


# --- transfer scoring ------------------------------------------------------

def test_transfer_score_requires_evidence():
    with pytest.raises(GeneralizationEvalError, match="transfer_score_requires_evidence"):
        score_transfer(
            {
                "score_id": "sc-2",
                "case_ref": "ho-1",
                "rubric": _rubric(),
                "met_criteria": ["defines held-out case", "demands evidence"],
                "evidence_refs": [],
            }
        )


def test_transfer_score_is_advisory_only():
    score = score_transfer(
        {
            "score_id": "sc-3",
            "case_ref": "ho-1",
            "rubric": _rubric(),
            "met_criteria": ["defines held-out case", "demands evidence"],
            "evidence_refs": ["ev-1"],
        }
    )
    assert score["advisory_only"] is True
    assert score["tool_authorized"] is False
    assert score["passed"] is True


# --- claim scope -----------------------------------------------------------

def test_single_success_cannot_claim_general_competence():
    with pytest.raises(GeneralizationEvalError, match="single_success_cannot_claim_general_competence"):
        build_claim_scope(
            {"claim_id": "cs-1", "passed_case_refs": ["ho-1"], "asserted_scope": "general", "claim_boundary": BOUNDARY}
        )


def test_broad_competence_claim_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="broad_competence_claim_rejected"):
        build_claim_scope(
            {
                "claim_id": "cs-2",
                "passed_case_refs": ["ho-1", "ho-2", "ho-3"],
                "asserted_scope": "universal",
                "claim_boundary": BOUNDARY,
            }
        )


def test_claim_scope_limited_to_passed_heldout_cases():
    results = [
        {"case_ref": "ho-1", "status": "passed"},
        {"case_ref": "ho-2", "status": "fail"},
        {"case_ref": "ho-3", "status": "passed"},
    ]
    scope = bounded_claim_scope("cs-3", results, claim_boundary=BOUNDARY)
    assert scope["case_refs"] == ["ho-1", "ho-3"]
    assert scope["generalizes_beyond_tested_cases"] is False


# --- result recording ------------------------------------------------------

def test_failed_transfer_records_failure_memory_ref():
    with pytest.raises(GeneralizationEvalError, match="failed_transfer_requires_failure_memory_ref"):
        build_generalization_result(
            {
                "result_id": "res-4",
                "case_ref": "ho-1",
                "split_ref": "split-1",
                "status": "failed",
                "claim_boundary": BOUNDARY,
            }
        )


def test_failed_transfer_with_memory_ref_records():
    result = build_generalization_result(
        {
            "result_id": "res-5",
            "case_ref": "ho-1",
            "split_ref": "split-1",
            "status": "failed",
            "failure_memory_ref": "mem-fail-1",
            "claim_boundary": BOUNDARY,
        }
    )
    assert result["status"] == "failed"
    assert result["failure_memory_ref"] == "mem-fail-1"


def test_green_result_passes_full_chain():
    result = build_generalization_result(
        {
            "result_id": "res-6",
            "case_ref": "ho-1",
            "split_ref": "split-1",
            "status": "passed",
            "evidence_refs": ["ev-1"],
            "receipt_refs": ["rc-1"],
            "leakage_audit": _passing_leakage_audit(),
            "claim_boundary": BOUNDARY,
        }
    )
    assert result["status"] == "passed"
    assert result["advisory_only"] is True


# --- phase 27 / phase 30 hand-offs -----------------------------------------

def test_acquired_mini_task_requires_heldout_retest():
    with pytest.raises(GeneralizationEvalError, match="acquired_mini_task_requires_heldout_retest"):
        accept_acquired_mini_task({"mini_task_id": "mt-1"})


def test_acquired_mini_task_with_retest_builds_heldout_case():
    case = accept_acquired_mini_task({"mini_task_id": "mt-1", "heldout_case_ref": "ho-9"})
    assert case["schema"] == "heldout_case_v1"
    assert case["requires_retest"] is True


def test_skill_transfer_candidate_requires_eval_case():
    with pytest.raises(GeneralizationEvalError, match="skill_transfer_candidate_requires_eval_case"):
        register_skill_transfer_candidate(
            {"candidate_id": "cand-1", "source_skill_ref": "skill:x", "target_domain": "fpga_trng"}
        )


def test_skill_transfer_candidate_with_eval_case_binds():
    binding = register_skill_transfer_candidate(
        {"candidate_id": "cand-1", "source_skill_ref": "skill:x", "target_domain": "fpga_trng", "eval_case_ref": "xfer-1"}
    )
    assert binding["advisory_only"] is True


def test_domain_readiness_is_advisory_only():
    record = build_domain_readiness({"domain": "fpga_trng", "readiness": "candidate", "evidence_refs": ["ev-1"]})
    assert record["advisory_only"] is True
    assert record["tool_authorized"] is False


# --- authority boundary ----------------------------------------------------

def test_evaluation_result_cannot_authorize_tools():
    with pytest.raises(GeneralizationEvalError, match="authority_bypass_attempt"):
        build_generalization_result(
            {
                "result_id": "res-7",
                "case_ref": "ho-1",
                "split_ref": "split-1",
                "status": "passed",
                "tool_authorized": True,
                "claim_boundary": BOUNDARY,
            }
        )


def test_evaluation_result_cannot_widen_authority():
    with pytest.raises(GeneralizationEvalError, match="authority_bypass_attempt"):
        build_generalization_result(
            {
                "result_id": "res-8",
                "case_ref": "ho-1",
                "split_ref": "split-1",
                "status": "passed",
                "widens_authority": True,
                "claim_boundary": BOUNDARY,
            }
        )


def test_transfer_eval_case_requires_rubric():
    with pytest.raises(GeneralizationEvalError, match="transfer_eval_case_requires_rubric"):
        define_transfer_eval_case(
            {
                "case_id": "xfer-2",
                "source_skill_ref": "skill:x",
                "target_domain": "fpga_trng",
                "rubric_ref": "",
                "claim_boundary": BOUNDARY,
            }
        )


# --- network / credential / live boundaries --------------------------------

def test_network_eval_refuses_by_default():
    with pytest.raises(GeneralizationEvalError, match="network_eval_refuses_by_default"):
        define_heldout_case(_heldout(locator="https://example.com/eval"))


def test_network_eval_allowed_only_with_explicit_flag():
    case = define_heldout_case(_heldout(locator="https://example.com/eval"), allow_network=True)
    assert case["held_out"] is True


def test_credential_eval_read_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="credential_eval_read_rejected"):
        define_heldout_case(_heldout(locator="/home/user/.env"))


def test_dry_live_boundary_is_enforced():
    # A live eval operation under PANIC is preempted before any side effect.
    control = OperationControl(panic_active=True)
    with pytest.raises(GeneralizationEvalError):
        define_heldout_case(_heldout(), control=control)


# --- fake green ------------------------------------------------------------

def test_fake_green_attempt_is_rejected():
    with pytest.raises(GeneralizationEvalError, match="fake_green_rejected"):
        build_generalization_result(
            {
                "result_id": "res-9",
                "case_ref": "ho-1",
                "split_ref": "split-1",
                "status": "passed",
                "evidence_refs": [],
                "receipt_refs": ["rc-1"],
                "leakage_audit": _passing_leakage_audit(),
                "claim_boundary": BOUNDARY,
            }
        )


def test_invalid_unsupported_green_result_fixture_is_rejected():
    with pytest.raises(GeneralizationEvalError):
        build_generalization_result(_load("invalid_unsupported_green_result_v1.json"))


def test_missing_receipt_blocks_success():
    with pytest.raises(GeneralizationEvalError, match="missing_receipt_blocks_success"):
        build_generalization_receipt(status="passed", receipt_refs=[])


def test_schema_violation_blocks_success():
    with pytest.raises(GeneralizationEvalError, match="schema_violation:missing"):
        build_generalization_result({"result_id": "res-10"})


# --- stop / panic preemption -----------------------------------------------

def test_stop_panic_preempts_eval_operation():
    control = OperationControl(panic_active=True)
    with pytest.raises(GeneralizationEvalError, match="REFUSED_PANIC"):
        score_transfer(
            {
                "score_id": "sc-4",
                "case_ref": "ho-1",
                "rubric": _rubric(),
                "met_criteria": ["defines held-out case"],
                "evidence_refs": ["ev-1"],
            },
            control=control,
        )


# --- replay ----------------------------------------------------------------

def test_replay_is_deterministic(tmp_path):
    log = GeneralizationEvalLog(tmp_path / "eval.jsonl")
    log.append("generalization_result_v1", {"result_id": "res-1", "status": "failed"})
    log.append("generalization_result_v1", {"result_id": "res-2", "status": "passed"})
    result = log.replay()
    assert result.ok is True
    assert result.records == 2


def test_replay_divergence_is_failure(tmp_path):
    path = tmp_path / "eval.jsonl"
    log = GeneralizationEvalLog(path)
    log.append("generalization_result_v1", {"result_id": "res-1", "status": "failed"})
    log.append("generalization_result_v1", {"result_id": "res-2", "status": "passed"})
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["payload"]["status"] = "passed"
    lines[0] = json.dumps(tampered, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = GeneralizationEvalLog(path).replay()
    assert result.ok is False
    assert any("payload_hash_mismatch" in e for e in result.errors)


def test_replay_under_panic_is_refused(tmp_path):
    log = GeneralizationEvalLog(tmp_path / "eval.jsonl")
    log.append("generalization_result_v1", {"result_id": "res-1", "status": "failed"})
    with pytest.raises(GeneralizationEvalError):
        log.replay(control=OperationControl(panic_active=True))


# --- gate ------------------------------------------------------------------

def _green_gate_kwargs(**overrides):
    kwargs = dict(
        phase27_green=True,
        phase30_green=True,
        proof_bundle=Path("dummy"),
        tests_passed=True,
        report_exists=True,
        heldout_cases_exclude_answer_keys=True,
        leakage_audit_required=True,
        surface_similarity_rejected=True,
        negative_controls_fail_expectedly=True,
        claim_scope_bounded_to_passed_cases=True,
        evaluation_result_cannot_authorize_tools=True,
        evaluation_result_cannot_widen_authority=True,
        single_success_cannot_claim_general_competence=True,
        network_eval_refuses_by_default=True,
        credential_eval_reads_rejected=True,
        fake_green_rejected=True,
        replay_deterministic=True,
        no_live_side_effect_path_by_default=True,
    )
    kwargs.update(overrides)
    return kwargs


def _make_bundle(tmp_path):
    for name in ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]:
        (tmp_path / name).write_text("{}" if name.endswith(".json") else "x", encoding="utf-8")
    (tmp_path / "gate_result.json").write_text(json.dumps({"proof_bundle": str(tmp_path)}), encoding="utf-8")
    return tmp_path


def test_phase31_gate_green_when_all_checks_pass(tmp_path):
    bundle = _make_bundle(tmp_path)
    result = evaluate_phase31_gate(**_green_gate_kwargs(proof_bundle=bundle))
    assert result["verdict"] == "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_31_GENERALIZATION_EVALUATION_HARNESS"
    assert result["ok"] is True


def test_phase31_gate_refuses_without_phase27_phase30_green(tmp_path):
    bundle = _make_bundle(tmp_path)
    no27 = evaluate_phase31_gate(**_green_gate_kwargs(proof_bundle=bundle, phase27_green=False))
    no30 = evaluate_phase31_gate(**_green_gate_kwargs(proof_bundle=bundle, phase30_green=False))
    assert no27["ok"] is False
    assert no30["ok"] is False


def test_phase31_gate_refuses_without_proof_bundle():
    result = evaluate_phase31_gate(**_green_gate_kwargs(proof_bundle=None))
    assert result["ok"] is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in result["failures"])


def test_proof_bundle_validator_flags_missing_files(tmp_path):
    ok, failures = validate_phase31_proof_bundle(tmp_path)
    assert ok is False
    assert failures
