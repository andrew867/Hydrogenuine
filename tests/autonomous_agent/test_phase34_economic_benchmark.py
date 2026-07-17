"""Phase 34 economic-task-benchmark-suite tests.

A benchmark result is evidence, not authority. A pass is not permission, not
deployment approval, not a live-action permit, and not broad competence. The suite
must never let a report claim AGI or the ability to perform any economic task, never
let a score authorize tools or create live effects, never hide failed cases, safety
failures, or human disagreement, and never skip artifact hashes or verifiers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.economic_benchmark import (
    EconomicBenchmarkError,
    EconomicBenchmarkLog,
    assert_candidate_is_advisory,
    assert_claim_not_widened,
    assert_not_fake_green,
    assert_not_permission,
    build_benchmark_run_receipt,
    build_claim_scope,
    create_benchmark_suite,
    create_task_case,
    define_verifier,
    enforce_dry_live_boundary,
    evaluate_case,
    generate_suite_result,
    map_case_to_domain_pack,
    propose_field_trial_candidate,
    record_artifact,
    record_artifact_hash,
    record_cost,
    record_evidence_quality,
    record_human_disagreement,
    record_human_review,
    record_model_cost,
    record_safety_result,
    reject_network_and_credentials,
    run_verification,
    verify_artifact_hash,
)
from hg_runtime.economic_benchmark.gate import (
    VERDICT_GREEN,
    evaluate_phase34_gate,
    validate_phase34_proof_bundle,
)
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_RESULT_SCHEMA,
    ECONOMIC_TASK_CASE_SCHEMA,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_text,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "phase34"
PANIC = OperationControl(panic_active=True)
STOP = OperationControl(stop_active=True)


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Builders for a complete passing case chain.                                 #
# --------------------------------------------------------------------------- #
def _verifier():
    return define_verifier({"verifier_id": "verifier-rubric-1", "kind": "rubric"})


def _passing_verification(case_ref="case-1"):
    return run_verification(_verifier(), case_ref=case_ref, passed=True, evidence_refs=["ev-1"])


def _failing_verification(case_ref="case-1"):
    return run_verification(_verifier(), case_ref=case_ref, passed=False, detail="rubric not met")


def _safety(case_ref="case-1", passed=True):
    return record_safety_result({"case_ref": case_ref, "passed": passed})


def _verified_artifact_hash(case_ref="case-1"):
    artifact = record_artifact({"artifact_id": "wb-artifact-1", "case_ref": case_ref, "content": "release note body"})
    record = record_artifact_hash(artifact)
    return verify_artifact_hash(artifact, record)


def _case(**overrides):
    payload = dict(_load("valid_economic_task_case_v1.json"))
    payload.update(overrides)
    return create_task_case(payload)


def _passing_outcome(case_ref="case-1", held_out=True, requires_human_review=False):
    case = _case(case_id=case_ref, held_out=held_out, requires_human_review=requires_human_review)
    return evaluate_case(
        case,
        verification_result=_passing_verification(case_ref),
        safety_record=_safety(case_ref),
        artifact_hash_record=_verified_artifact_hash(case_ref),
        human_review=None,
    )


def _negative_control_outcome(case_ref="nc-1"):
    """A negative control that correctly FAILS (its verifier does not pass)."""
    case = _case(case_id=case_ref, is_negative_control=True, held_out=True, requires_human_review=False)
    case = dict(case)
    case["is_negative_control"] = True
    return evaluate_case(
        case,
        verification_result=_failing_verification(case_ref),
        safety_record=_safety(case_ref),
        artifact_hash_record=_verified_artifact_hash(case_ref),
    )


# --------------------------------------------------------------------------- #
# Claim-boundary tests.                                                       #
# --------------------------------------------------------------------------- #
def test_benchmark_report_cannot_claim_agi():
    with pytest.raises(EconomicBenchmarkError, match="agi_claim_rejected"):
        build_claim_scope({"suite_ref": "s1", "statement": "This proves AGI is achieved."})
    with pytest.raises(EconomicBenchmarkError, match="agi_claim_rejected"):
        reject_forbidden_claim_text("artificial general intelligence demonstrated")


def test_benchmark_report_cannot_claim_any_economic_task():
    with pytest.raises(EconomicBenchmarkError, match="any_economic_task_claim_rejected"):
        build_claim_scope({"suite_ref": "s1", "statement": "The agent can perform any economic task a human can."})


def test_benchmark_report_cannot_claim_human_level_or_broad_competence():
    with pytest.raises(EconomicBenchmarkError, match="human_level_capability_claim_rejected"):
        build_claim_scope({"suite_ref": "s1", "statement": "Achieves human-level economic capability."})
    with pytest.raises(EconomicBenchmarkError, match="broad_competence_claim_rejected"):
        build_claim_scope({"suite_ref": "s1", "statement": "Shows broad competence across the economy."})


def test_agi_token_does_not_false_match_ordinary_words():
    # "again" / "imagine" must not trip the AGI guard.
    scope = build_claim_scope({"suite_ref": "s1", "statement": "We ran the rubric again to imagine edge cases."})
    assert scope["claims_agi"] is False


# --------------------------------------------------------------------------- #
# Case-definition requirement tests.                                          #
# --------------------------------------------------------------------------- #
def test_task_case_requires_verifier():
    with pytest.raises(EconomicBenchmarkError, match="task_case_requires_verifier"):
        _case(verifier_ref="")


def test_benchmark_case_requires_domain_pack_mapping():
    with pytest.raises(EconomicBenchmarkError, match="benchmark_case_requires_domain_pack_mapping"):
        _case(domain_pack_mapping_ref="")


def test_benchmark_case_requires_workbench_artifact_ref():
    with pytest.raises(EconomicBenchmarkError, match="benchmark_case_requires_workbench_artifact_ref"):
        _case(workbench_artifact_ref="")


def test_benchmark_case_requires_evidence_quality_record():
    with pytest.raises(EconomicBenchmarkError, match="benchmark_case_requires_evidence_quality_record"):
        _case(evidence_quality_ref="")


def test_benchmark_case_requires_cost_record():
    with pytest.raises(EconomicBenchmarkError, match="benchmark_case_requires_cost_record"):
        _case(cost_record_ref="")


def test_benchmark_case_requires_safety_record():
    with pytest.raises(EconomicBenchmarkError, match="benchmark_case_requires_safety_record"):
        _case(safety_record_ref="")


def test_benchmark_case_requires_claim_scope():
    with pytest.raises(EconomicBenchmarkError, match="benchmark_case_requires_claim_scope"):
        _case(claim_scope_ref="")


def test_valid_case_from_fixture_builds():
    case = _case()
    assert case["schema"] == ECONOMIC_TASK_CASE_SCHEMA
    assert case["advisory_only"] is True
    assert case["permission_granted"] is False


def test_invalid_case_fixture_is_rejected():
    payload = _load("invalid_task_case_no_verifier_v1.json")
    with pytest.raises(EconomicBenchmarkError, match="task_case_requires_verifier"):
        create_task_case(payload)


# --------------------------------------------------------------------------- #
# Authority / permission boundary tests.                                      #
# --------------------------------------------------------------------------- #
def test_benchmark_pass_is_not_permission():
    outcome = _passing_outcome()
    assert outcome["green"] is True
    assert outcome["permission_granted"] is False
    assert outcome["is_permission"] is False
    assert_not_permission(outcome)
    with pytest.raises(EconomicBenchmarkError, match="benchmark_is_not_permission"):
        assert_not_permission({"pass_as_permission": True})


def test_benchmark_score_cannot_authorize_tools():
    with pytest.raises(EconomicBenchmarkError, match="authority_bypass_attempt"):
        reject_authority_payload({"score_authorizes_tool": True})


def test_benchmark_score_cannot_create_live_effects():
    with pytest.raises(EconomicBenchmarkError, match="authority_bypass_attempt"):
        reject_authority_payload({"live_side_effects_created": True})


def test_benchmark_result_cannot_widen_authority():
    with pytest.raises(EconomicBenchmarkError, match="authority_bypass_attempt"):
        reject_authority_payload({"widens_authority": True})


def test_benchmark_result_cannot_widen_claim_scope():
    scope = build_claim_scope({"suite_ref": "s1", "statement": "Bounded to verified cases.", "supporting_case_refs": ["case-1"]})
    with pytest.raises(EconomicBenchmarkError, match="benchmark_result_cannot_widen_claim_scope"):
        assert_claim_not_widened(scope, allowed_case_refs=["case-2"])


def test_neutral_flags_are_all_false():
    assert all(value is False for value in neutral_flags().values())


# --------------------------------------------------------------------------- #
# Outcome / gating tests.                                                      #
# --------------------------------------------------------------------------- #
def test_failed_case_is_recorded_not_hidden():
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    failing = evaluate_case(
        _case(case_id="case-fail"),
        verification_result=_failing_verification("case-fail"),
        safety_record=_safety("case-fail"),
        artifact_hash_record=_verified_artifact_hash("case-fail"),
    )
    result = generate_suite_result(
        suite,
        [failing],
        negative_control_outcomes=[_negative_control_outcome()],
        receipt_refs=["rcpt-1"],
    )
    assert "case-fail" in result["failed_case_ids"]
    assert any(o["case_id"] == "case-fail" for o in result["cases"])
    assert result["green"] is False


def test_safety_failure_blocks_green_even_if_score_high():
    outcome = evaluate_case(
        _case(case_id="case-1"),
        verification_result=_passing_verification(),
        safety_record=_safety(passed=False),
        artifact_hash_record=_verified_artifact_hash(),
    )
    assert outcome["green"] is False
    assert "safety_failed" in outcome["reasons"]


def test_verification_failure_blocks_green():
    outcome = evaluate_case(
        _case(case_id="case-1"),
        verification_result=_failing_verification(),
        safety_record=_safety(),
        artifact_hash_record=_verified_artifact_hash(),
    )
    assert outcome["green"] is False
    assert "verification_failed" in outcome["reasons"]


def test_missing_artifact_hash_blocks_green():
    outcome = evaluate_case(
        _case(case_id="case-1"),
        verification_result=_passing_verification(),
        safety_record=_safety(),
        artifact_hash_record=None,
    )
    assert outcome["green"] is False
    assert "missing_artifact_hash" in outcome["reasons"]


def test_artifact_hash_required_for_green():
    # An unverified hash record (verified flag false) is not enough.
    artifact = record_artifact({"artifact_id": "a1", "case_ref": "case-1", "content": "body"})
    unverified = record_artifact_hash(artifact)
    outcome = evaluate_case(
        _case(case_id="case-1"),
        verification_result=_passing_verification(),
        safety_record=_safety(),
        artifact_hash_record=unverified,
    )
    assert outcome["green"] is False
    assert "artifact_hash_unverified" in outcome["reasons"]


def test_missing_verifier_blocks_green():
    outcome = evaluate_case(
        _case(case_id="case-1"),
        verification_result=None,
        safety_record=_safety(),
        artifact_hash_record=_verified_artifact_hash(),
    )
    assert "missing_verifier" in outcome["reasons"]


def test_missing_human_review_record_blocks_green_when_required():
    outcome = evaluate_case(
        _case(case_id="case-1", requires_human_review=True),
        verification_result=_passing_verification(),
        safety_record=_safety(),
        artifact_hash_record=_verified_artifact_hash(),
        human_review=None,
    )
    assert outcome["green"] is False
    assert "missing_human_review" in outcome["reasons"]


def test_human_disagreement_prevents_unqualified_green():
    review = record_human_review(
        {"case_ref": "case-1", "reviewer": "r1", "verdict": "pass", "disagreements": ["r2 disagrees"]}
    )
    assert review["disagreement_unresolved"] is True
    outcome = evaluate_case(
        _case(case_id="case-1", requires_human_review=True),
        verification_result=_passing_verification(),
        safety_record=_safety(),
        artifact_hash_record=_verified_artifact_hash(),
        human_review=review,
    )
    assert outcome["green"] is False
    assert outcome["status"] == "qualified"


def test_human_review_disagreement_is_recorded():
    record = record_human_disagreement(
        {"case_ref": "case-1", "reviewer_a": "r1", "reviewer_b": "r2", "verdict_a": "pass", "verdict_b": "fail"}
    )
    assert record["hidden"] is False
    assert record["resolved"] is False


def test_passing_case_is_green():
    outcome = _passing_outcome()
    assert outcome["green"] is True
    assert outcome["status"] == "pass"
    assert outcome["reasons"] == []


# --------------------------------------------------------------------------- #
# Cost / domain / artifact advisory tests.                                    #
# --------------------------------------------------------------------------- #
def test_cost_record_includes_model_route_receipt():
    with pytest.raises(EconomicBenchmarkError, match="cost_record_requires_model_route_receipt"):
        record_cost({"case_ref": "case-1", "used_model": True})
    ok = record_cost({"case_ref": "case-1", "used_model": True, "model_route_receipt_ref": "mr-1"})
    assert ok["model_route_receipt_ref"] == "mr-1"


def test_model_route_receipt_is_advisory_only():
    record = record_model_cost(_load("valid_model_cost_record_v1.json"))
    assert record["advisory_only"] is True
    assert record["model_route_is_permission"] is False
    assert record["permission_granted"] is False


def test_domain_pack_is_advisory_only():
    mapping = map_case_to_domain_pack({"case_ref": "case-1", "domain_pack_ref": "pack-writing"})
    assert mapping["advisory_only"] is True
    assert mapping["domain_pack_is_permission"] is False


def test_workbench_artifact_is_not_truth_without_verification():
    artifact = record_artifact({"artifact_id": "a1", "case_ref": "case-1", "content": "x"})
    assert artifact["verified"] is False
    tampered = dict(artifact)
    tampered["content"] = "y"
    record = record_artifact_hash(artifact)
    with pytest.raises(EconomicBenchmarkError, match="artifact_hash_mismatch"):
        verify_artifact_hash(tampered, record)


def test_evidence_quality_is_advisory_and_does_not_gate():
    record = record_evidence_quality({"case_ref": "case-1", "tier": "strong"})
    assert record["advisory_only"] is True
    assert record["gates_green"] is False


# --------------------------------------------------------------------------- #
# Generalization / field-trial tests.                                         #
# --------------------------------------------------------------------------- #
def test_generalization_scope_bounds_benchmark_claims():
    passed = _passing_outcome(case_ref="case-1", held_out=True)
    scope = build_claim_scope(
        {"suite_ref": "s1", "statement": "Supported by held-out verified cases."},
        outcomes=[passed],
    )
    assert scope["supporting_case_refs"] == ["case-1"]
    with pytest.raises(EconomicBenchmarkError, match="claim_scope_overreaches_unverified_cases"):
        build_claim_scope(
            {"suite_ref": "s1", "statement": "Supported.", "supporting_case_refs": ["case-unverified"]},
            outcomes=[passed],
        )


def test_heldout_scope_required_for_field_trial_candidate():
    not_heldout = _passing_outcome(case_ref="case-1", held_out=False)
    with pytest.raises(EconomicBenchmarkError, match="heldout_scope_required_for_field_trial_candidate"):
        propose_field_trial_candidate(
            {"candidate_id": "ft-1", "suite_ref": "s1", "case_ref": "case-1"},
            outcome=not_heldout,
        )


def test_field_trial_candidate_requires_passed_verified_scope():
    failed = evaluate_case(
        _case(case_id="case-1"),
        verification_result=_failing_verification(),
        safety_record=_safety(),
        artifact_hash_record=_verified_artifact_hash(),
    )
    with pytest.raises(EconomicBenchmarkError, match="field_trial_candidate_requires_passed_verified_scope"):
        propose_field_trial_candidate(
            {"candidate_id": "ft-1", "suite_ref": "s1", "case_ref": "case-1"},
            outcome=failed,
        )


def test_field_trial_candidate_is_advisory_only():
    passed = _passing_outcome(case_ref="case-1", held_out=True)
    candidate = propose_field_trial_candidate(
        {"candidate_id": "ft-1", "suite_ref": "s1", "case_ref": "case-1"},
        outcome=passed,
    )
    assert candidate["advisory_only"] is True
    assert candidate["requires_phase35_regating"] is True
    assert candidate["is_live_permit"] is False
    assert_candidate_is_advisory(candidate)
    with pytest.raises(EconomicBenchmarkError, match="field_trial_candidate_is_advisory_only"):
        assert_candidate_is_advisory({**candidate, "is_live_permit": True})


# --------------------------------------------------------------------------- #
# Suite-level / negative-control / leakage tests.                             #
# --------------------------------------------------------------------------- #
def test_negative_control_required_for_suite():
    with pytest.raises(EconomicBenchmarkError, match="suite_requires_negative_control"):
        create_benchmark_suite(_load("invalid_suite_no_negative_control_v1.json"))
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    result = generate_suite_result(suite, [_passing_outcome()], negative_control_outcomes=[], receipt_refs=["r1"])
    assert result["green"] is False
    assert "negative_control_required" in result["reasons"]


def test_negative_control_passes_unexpectedly_blocks_green():
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    bad_control = _passing_outcome(case_ref="nc-1", held_out=True)
    bad_control = {**bad_control, "is_negative_control": True}
    result = generate_suite_result(
        suite,
        [_passing_outcome()],
        negative_control_outcomes=[bad_control],
        receipt_refs=["r1"],
    )
    assert result["green"] is False
    assert "negative_control_passes_unexpectedly" in result["reasons"]


def test_benchmark_leakage_blocks_green():
    leaked = evaluate_case(
        _case(case_id="case-1"),
        verification_result=_passing_verification(),
        safety_record=_safety(),
        artifact_hash_record=_verified_artifact_hash(),
        leakage_detected=True,
    )
    assert leaked["green"] is False
    assert "leakage_detected" in leaked["reasons"]
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    result = generate_suite_result(
        suite,
        [_passing_outcome()],
        negative_control_outcomes=[_negative_control_outcome()],
        receipt_refs=["r1"],
        leakage_detected=True,
    )
    assert result["green"] is False
    assert "leakage_detected" in result["reasons"]


def test_clean_suite_is_green():
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    result = generate_suite_result(
        suite,
        [_passing_outcome()],
        negative_control_outcomes=[_negative_control_outcome()],
        receipt_refs=["rcpt-1"],
    )
    assert result["schema"] == BENCHMARK_RESULT_SCHEMA
    assert result["green"] is True
    assert result["passed_verified_heldout_case_ids"] == ["case-1"]
    assert_not_fake_green(result)


# --------------------------------------------------------------------------- #
# Fake green / receipt / schema tests.                                        #
# --------------------------------------------------------------------------- #
def test_fake_green_attempt_is_rejected():
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    failing = evaluate_case(
        _case(case_id="case-fail"),
        verification_result=_failing_verification("case-fail"),
        safety_record=_safety("case-fail"),
        artifact_hash_record=_verified_artifact_hash("case-fail"),
    )
    result = generate_suite_result(
        suite, [failing], negative_control_outcomes=[_negative_control_outcome()], receipt_refs=["r1"]
    )
    forged = {**result, "green": True, "status": "green"}
    with pytest.raises(EconomicBenchmarkError, match="fake_green_rejected"):
        assert_not_fake_green(forged)


def test_missing_receipt_blocks_success():
    with pytest.raises(EconomicBenchmarkError, match="missing_receipt_blocks_success"):
        build_benchmark_run_receipt(suite_ref="s1", status="green", receipt_refs=[])
    suite = create_benchmark_suite(_load("valid_benchmark_suite_v1.json"))
    result = generate_suite_result(
        suite, [_passing_outcome()], negative_control_outcomes=[_negative_control_outcome()], receipt_refs=[]
    )
    assert result["green"] is False
    assert "missing_receipt" in result["reasons"]


def test_schema_violation_blocks_success():
    with pytest.raises(EconomicBenchmarkError, match="schema_violation:missing"):
        create_benchmark_suite({"title": "no id", "domain": "x", "negative_control_refs": ["nc"]})


def test_run_receipt_is_advisory_and_not_permission():
    receipt = build_benchmark_run_receipt(suite_ref="s1", status="green", receipt_refs=["r1"])
    assert receipt["is_permission"] is False
    assert receipt["advisory_only"] is True


# --------------------------------------------------------------------------- #
# Network / credential / dry-live tests.                                       #
# --------------------------------------------------------------------------- #
def test_network_benchmark_refuses_by_default():
    with pytest.raises(EconomicBenchmarkError, match="network_benchmark_refuses_by_default"):
        create_task_case(_load("invalid_network_benchmark_case_v1.json"))
    # explicit allow_network lets a network locator through.
    case = create_task_case(_load("invalid_network_benchmark_case_v1.json"), allow_network=True)
    assert case["case_id"] == "case-network"


def test_credential_benchmark_read_is_rejected():
    with pytest.raises(EconomicBenchmarkError, match="credential_benchmark_read_rejected"):
        reject_network_and_credentials("/home/user/.env")
    with pytest.raises(EconomicBenchmarkError, match="credential_benchmark_read_rejected"):
        create_task_case(_case_payload(input_locator="secrets/api_key.txt"))


def _case_payload(**overrides):
    payload = dict(_load("valid_economic_task_case_v1.json"))
    payload.update(overrides)
    return payload


def test_dry_live_boundary_is_enforced():
    assert enforce_dry_live_boundary(live=False) == "dry"
    with pytest.raises(EconomicBenchmarkError, match="dry_live_boundary_enforced"):
        enforce_dry_live_boundary(live=True, operator_permit_refs=[])
    assert enforce_dry_live_boundary(live=True, operator_permit_refs=["permit-1"]) == "live"


# --------------------------------------------------------------------------- #
# STOP / PANIC and replay tests.                                               #
# --------------------------------------------------------------------------- #
def test_stop_panic_preempts_benchmark_operation():
    with pytest.raises(EconomicBenchmarkError, match="REFUSED_PANIC"):
        create_benchmark_suite(_load("valid_benchmark_suite_v1.json"), control=PANIC)
    with pytest.raises(EconomicBenchmarkError, match="REFUSED_STOP"):
        evaluate_case(
            _case(case_id="case-1"),
            verification_result=_passing_verification(),
            safety_record=_safety(),
            artifact_hash_record=_verified_artifact_hash(),
            control=STOP,
        )


def test_replay_is_deterministic(tmp_path):
    log = EconomicBenchmarkLog(tmp_path / "bench.jsonl")
    log.append("benchmark_result_v1", {"suite_ref": "s1", "green": True})
    log.append("benchmark_run_receipt_v1", {"suite_ref": "s1", "status": "green"})
    first = log.replay()
    assert first.ok is True
    assert first.records == 2
    reopened = EconomicBenchmarkLog(tmp_path / "bench.jsonl")
    second = reopened.replay()
    assert second.ok is True
    assert second.chain_root == first.chain_root


def test_replay_divergence_is_failure(tmp_path):
    path = tmp_path / "bench.jsonl"
    log = EconomicBenchmarkLog(path)
    log.append("benchmark_result_v1", {"suite_ref": "s1", "green": True})
    rec = log.append("benchmark_result_v1", {"suite_ref": "s1", "green": False})
    lines = path.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[1])
    data["payload"]["green"] = True  # tamper
    lines[1] = json.dumps(data, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = EconomicBenchmarkLog(path).replay()
    assert result.ok is False
    assert any("payload_hash_mismatch" in err for err in result.errors)


def test_replay_preempted_by_panic(tmp_path):
    log = EconomicBenchmarkLog(tmp_path / "bench.jsonl")
    log.append("benchmark_result_v1", {"suite_ref": "s1"})
    with pytest.raises(EconomicBenchmarkError, match="REFUSED_PANIC"):
        log.replay(control=PANIC)


# --------------------------------------------------------------------------- #
# Gate tests.                                                                  #
# --------------------------------------------------------------------------- #
def _valid_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"):
        (bundle / name).write_text("{}\n" if name.endswith(".json") else "x\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(json.dumps({"proof_bundle": str(bundle)}) + "\n", encoding="utf-8")
    return bundle


def _green_kwargs(bundle):
    return dict(
        phase28_green=True,
        phase29_green=True,
        phase30_green=True,
        phase31_green=True,
        phase32_green=True,
        phase33_green=True,
        proof_bundle=bundle,
        tests_passed=True,
        report_exists=True,
        benchmark_report_cannot_claim_agi=True,
        benchmark_report_cannot_claim_any_economic_task=True,
        task_case_requires_verifier=True,
        artifact_hash_required_for_green=True,
        human_review_disagreement_recorded=True,
        safety_failure_blocks_green=True,
        verification_failure_blocks_green=True,
        failed_cases_preserved=True,
        benchmark_result_cannot_authorize_tools=True,
        benchmark_result_cannot_create_live_effects=True,
        benchmark_result_cannot_widen_authority=True,
        claim_scope_bounded_to_verified_heldout=True,
        field_trial_candidate_is_advisory_only=True,
        model_route_cost_records_advisory_only=True,
        benchmark_leakage_blocks_green=True,
        negative_control_required=True,
        network_benchmark_refuses_by_default=True,
        credential_reads_rejected=True,
        fake_green_rejected=True,
        replay_deterministic=True,
        stop_panic_preemption_preserved=True,
        no_live_side_effect_path_by_default=True,
    )


def test_phase34_gate_green_path(tmp_path):
    bundle = _valid_bundle(tmp_path)
    result = evaluate_phase34_gate(**_green_kwargs(bundle))
    assert result["verdict"] == VERDICT_GREEN
    assert result["ok"] is True
    assert result["benchmark_report_can_claim_agi"] is False


def test_phase34_gate_refuses_without_phase28_to_phase33_green(tmp_path):
    bundle = _valid_bundle(tmp_path)
    kwargs = _green_kwargs(bundle)
    kwargs["phase30_green"] = False
    result = evaluate_phase34_gate(**kwargs)
    assert result["ok"] is False
    assert any("PHASE30_GREEN_REQUIRED" in f for f in result["failures"])


def test_phase34_gate_refuses_without_proof_bundle(tmp_path):
    kwargs = _green_kwargs(None)
    result = evaluate_phase34_gate(**kwargs)
    assert result["ok"] is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in result["failures"])


def test_phase34_gate_refuses_on_safety_check_fail(tmp_path):
    bundle = _valid_bundle(tmp_path)
    kwargs = _green_kwargs(bundle)
    kwargs["safety_failure_blocks_green"] = False
    result = evaluate_phase34_gate(**kwargs)
    assert result["ok"] is False
    assert any("SAFETY_FAILURE_BLOCKS_GREEN_FAIL" in f for f in result["failures"])


def test_proof_bundle_validator_detects_missing_files(tmp_path):
    bundle = tmp_path / "incomplete"
    bundle.mkdir()
    (bundle / "HEAD.txt").write_text("x\n", encoding="utf-8")
    ok, failures = validate_phase34_proof_bundle(bundle)
    assert ok is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in failures)
