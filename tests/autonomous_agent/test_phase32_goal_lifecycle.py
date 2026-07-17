"""Phase 32 long-horizon-goal-lifecycle tests.

The lifecycle turns operator intent into durable goals, tasks, and outcomes across
sessions. It must never self-authorize work, continue through STOP/PANIC, execute
live actions, bypass GPP/HAL/UEAK, or treat a goal/plan/evidence/capability as
permission.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle import (
    GoalLifecycleError,
    GoalLifecycleLog,
    apply_panic,
    apply_stop,
    ask_operator,
    attach_advisory_evidence,
    bind_receipt,
    build_lifecycle_receipt,
    candidate_task_from_failed_gate,
    create_candidate_task,
    create_goal,
    create_replan,
    create_subgoal,
    define_allowed_task_class,
    intake_operator_intent,
    is_ambiguous,
    record_failure,
    record_outcome,
    require_ask_operator,
    resume_goal,
    select_work_item,
    transition_goal,
    validate_allowed_task_class,
)
from hg_runtime.goal_lifecycle.gate import (
    evaluate_phase32_gate,
    validate_phase32_proof_bundle,
)
from hg_runtime.goal_lifecycle.schemas import (
    ACTIVE,
    PANIC_HALTED,
    STOPPED,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "phase32"
BOUNDARY = "goal_lifecycle_advisory_default"
PANIC = OperationControl(panic_active=True)
STOP = OperationControl(stop_active=True)


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _scoped_intent(**overrides):
    payload = {
        "intent_id": "intent-1",
        "statement": "Stand up a reproducible entropy-validation gate for the FPGA TRNG.",
        "scope": "fpga_trng_validation_internal",
        "success_criteria": ["held-out case exists", "gate reads gate_result.json"],
        "claim_boundary": BOUNDARY,
    }
    payload.update(overrides)
    return intake_operator_intent(payload)


def _goal(**overrides):
    payload = {"goal_id": "goal-1"}
    payload.update(overrides)
    return create_goal(_scoped_intent(), payload)


def _allowed_classes():
    return [define_allowed_task_class({"task_class_id": "remediation", "description": "fix a failed gate"})]


# --- operator intent & ambiguity -------------------------------------------

def test_operator_intent_requires_scope():
    intent = intake_operator_intent(
        {"intent_id": "i-noscope", "statement": "do the entropy thing", "claim_boundary": BOUNDARY}
    )
    assert intent["ambiguous"] is True
    with pytest.raises(GoalLifecycleError, match="operator_intent_requires_scope"):
        create_goal(intent, {"goal_id": "g-x"})


def test_ambiguous_goal_enters_ask_operator():
    intent = intake_operator_intent(_load("invalid_ambiguous_intent_v1.json"))
    assert intent["requires_ask_operator"] is True
    assert intent["status"] == "ask_operator"


def test_ambiguous_intent_does_not_create_active_goal():
    intent = intake_operator_intent(_load("invalid_ambiguous_intent_v1.json"))
    with pytest.raises(GoalLifecycleError, match="ambiguous_intent_cannot_create_active_goal"):
        create_goal(intent, {"goal_id": "g-amb"})


def test_ask_operator_record_required_for_ambiguity():
    intent = intake_operator_intent(_load("invalid_ambiguous_intent_v1.json"))
    with pytest.raises(GoalLifecycleError, match="ask_operator_record_required_for_ambiguity"):
        require_ask_operator(intent, None)
    record = ask_operator(
        {"question_id": "q-1", "intent_ref": intent["intent_id"], "question": "Which subsystem?", "claim_boundary": BOUNDARY}
    )
    assert require_ask_operator(intent, record)["question_id"] == "q-1"


def test_scoped_intent_is_not_ambiguous():
    intent = _scoped_intent()
    assert is_ambiguous(intent) is False
    assert intent["scoped"] is True


# --- goals & subgoals ------------------------------------------------------

def test_goal_created_from_scoped_intent_is_active():
    goal = _goal()
    assert goal["state"] == ACTIVE
    assert goal["intent_ref"] == "intent-1"


def test_subgoal_requires_parent_goal():
    with pytest.raises(GoalLifecycleError, match="subgoal_requires_parent_goal"):
        create_subgoal({"subgoal_id": "sg-1", "description": "build the gate"})


def test_subgoal_with_parent_is_created():
    sg = create_subgoal({"subgoal_id": "sg-1", "parent_goal_ref": "goal-1", "description": "build the gate"})
    assert sg["parent_goal_ref"] == "goal-1"


# --- goals cannot grant authority ------------------------------------------

def test_goal_cannot_grant_authority():
    with pytest.raises(GoalLifecycleError, match="authority_bypass_attempt"):
        create_goal(_scoped_intent(), {"goal_id": "g-auth", "grants_authority": True})


def test_goal_cannot_authorize_tools():
    with pytest.raises(GoalLifecycleError, match="authority_bypass_attempt"):
        create_goal(_scoped_intent(), {"goal_id": "g-tool", "tool_authorized": True})


def test_goal_cannot_create_live_effects():
    with pytest.raises(GoalLifecycleError, match="authority_bypass_attempt"):
        create_goal(_scoped_intent(), {"goal_id": "g-live", "live_side_effects_created": True})


def test_goal_cannot_bypass_gpp_hal_ueak():
    for key in ("override_gpp", "override_hal", "override_ueak"):
        with pytest.raises(GoalLifecycleError, match="authority_bypass_attempt"):
            create_goal(_scoped_intent(), {"goal_id": "g-bypass", key: True})


# --- candidate tasks & selection -------------------------------------------

def test_candidate_task_is_not_execution():
    task = create_candidate_task(
        {"task_id": "t-1", "goal_ref": "goal-1", "description": "build gate", "proposed_task_class": "remediation", "claim_boundary": BOUNDARY}
    )
    assert task["is_execution"] is False
    assert task["execution_allowed"] is False


def test_failed_gate_generates_candidate_task():
    gate_result = {"verdict": "RED_PHASE_X", "ok": False, "failures": ["RED_X_FAIL"]}
    task = candidate_task_from_failed_gate(gate_result, goal_ref="goal-1", task_id="t-remediate")
    assert task["proposed_task_class"] == "remediation"
    assert task["is_execution"] is False


def test_candidate_task_requires_allowed_class():
    task = create_candidate_task(
        {"task_id": "t-2", "goal_ref": "goal-1", "description": "x", "proposed_task_class": "unlisted_class", "claim_boundary": BOUNDARY}
    )
    with pytest.raises(GoalLifecycleError, match="candidate_task_requires_allowed_class"):
        validate_allowed_task_class(task, _allowed_classes())


def test_candidate_task_requires_allowed_class_before_execution():
    with pytest.raises(GoalLifecycleError, match="candidate_task_requires_allowed_class_before_execution"):
        select_work_item(
            {
                "work_item_id": "wi-1",
                "candidate_task_ref": "t-1",
                "allowed_class_ref": "",
                "authority_refs": ["gpp:1"],
                "receipt_plan": {"gate": "g"},
                "claim_boundary": BOUNDARY,
            }
        )


def test_selected_work_item_requires_authority_reference():
    with pytest.raises(GoalLifecycleError, match="selected_work_item_requires_authority_reference"):
        select_work_item(_load("invalid_work_item_missing_authority_v1.json"))


def test_selected_work_item_requires_receipt_plan():
    with pytest.raises(GoalLifecycleError, match="selected_work_item_requires_receipt_plan"):
        select_work_item(
            {
                "work_item_id": "wi-2",
                "candidate_task_ref": "t-1",
                "allowed_class_ref": "remediation",
                "authority_refs": ["gpp:1"],
                "receipt_plan": {},
                "claim_boundary": BOUNDARY,
            }
        )


def test_valid_work_item_is_selected():
    item = select_work_item(_load("valid_selected_work_item_v1.json"))
    assert item["authority_minted_here"] is False
    assert item["mode"] == "dry"
    assert item["authority_refs"]


# --- STOP / PANIC ----------------------------------------------------------

def test_stop_transitions_goal_to_stopped():
    goal = _goal()
    stopped, record = apply_stop(goal)
    assert stopped["state"] == STOPPED
    assert record["to_state"] == STOPPED


def test_panic_transitions_goal_to_panic_halted():
    goal = _goal()
    halted, record = apply_panic(goal)
    assert halted["state"] == PANIC_HALTED
    assert record["to_state"] == PANIC_HALTED


def test_goal_cannot_continue_after_panic():
    goal = _goal()
    halted, _ = apply_panic(goal)
    with pytest.raises(GoalLifecycleError, match="illegal_goal_transition"):
        transition_goal(halted, ACTIVE)


def test_durable_goal_resume_requires_non_panic_state():
    goal = _goal()
    halted, _ = apply_panic(goal)
    with pytest.raises(GoalLifecycleError, match="durable_goal_resume_requires_non_panic_state"):
        resume_goal(halted)


def test_resume_under_live_panic_is_refused():
    goal = _goal()
    stopped, _ = apply_stop(goal)
    with pytest.raises(GoalLifecycleError, match="REFUSED_PANIC"):
        resume_goal(stopped, control=PANIC)


def test_stopped_goal_can_resume_when_clear():
    goal = _goal()
    stopped, _ = apply_stop(goal)
    resumed, record = resume_goal(stopped)
    assert resumed["state"] == ACTIVE


def test_panic_blocks_task_selection():
    with pytest.raises(GoalLifecycleError, match="REFUSED_PANIC"):
        select_work_item(_load("valid_selected_work_item_v1.json"), control=PANIC)


def test_intake_under_panic_is_refused():
    with pytest.raises(GoalLifecycleError, match="REFUSED_PANIC"):
        intake_operator_intent(
            {"intent_id": "i", "statement": "x", "scope": "s", "success_criteria": ["c"], "claim_boundary": BOUNDARY},
            control=PANIC,
        )


# --- receipts, outcomes, failures ------------------------------------------

def test_failed_receipt_is_preserved():
    failure = record_failure(
        {"failure_id": "f-1", "goal_ref": "goal-1", "failure_reason": "entropy gate RED", "receipt_refs": ["rc-failed-1"]}
    )
    assert failure["preserved"] is True
    assert failure["hidden"] is False
    assert failure["receipt_refs"] == ["rc-failed-1"]


def test_missing_receipt_blocks_success():
    with pytest.raises(GoalLifecycleError, match="missing_receipt_blocks_success"):
        record_outcome(
            {"outcome_id": "o-1", "goal_ref": "goal-1", "status": "completed", "receipt_refs": [], "claim_boundary": BOUNDARY}
        )


def test_fake_green_attempt_is_rejected():
    with pytest.raises(GoalLifecycleError, match="fake_green_rejected"):
        record_outcome(
            {
                "outcome_id": "o-2",
                "goal_ref": "goal-1",
                "status": "completed",
                "receipt_refs": ["rc-1"],
                "gate_results": [{"verdict": "RED_X", "ok": False}],
                "claim_boundary": BOUNDARY,
            }
        )


def test_green_outcome_with_receipts_and_clean_gates():
    outcome = record_outcome(
        {
            "outcome_id": "o-3",
            "goal_ref": "goal-1",
            "status": "completed",
            "receipt_refs": ["rc-1"],
            "gate_results": [{"verdict": "GREEN_X", "ok": True}],
            "claim_boundary": BOUNDARY,
        }
    )
    assert outcome["status"] == "completed"


def test_receipt_binding_is_preserved():
    binding = bind_receipt({"goal_ref": "goal-1", "receipt_ref": "rc-1", "kind": "gate_result"})
    assert binding["preserved"] is True


def test_lifecycle_receipt_requires_receipts_for_green():
    with pytest.raises(GoalLifecycleError, match="missing_receipt_blocks_success"):
        build_lifecycle_receipt(goal_ref="goal-1", status="completed", receipt_refs=[])


# --- replanning ------------------------------------------------------------

def test_replan_preserves_failure_history():
    replan = create_replan(_load("valid_replan_record_v1.json"))
    assert replan["failure_history_preserved"] is True
    assert replan["prior_failure_refs"] == ["fail-entropy-gate-1"]


def test_replan_cannot_erase_receipts():
    with pytest.raises(GoalLifecycleError, match="replan_cannot_erase_receipts"):
        create_replan(_load("invalid_replan_erases_receipts_v1.json"))


def test_replan_must_preserve_failure_history():
    with pytest.raises(GoalLifecycleError, match="replan_must_preserve_failure_history"):
        create_replan(
            {"replan_id": "r-empty", "goal_ref": "goal-1", "prior_failure_refs": [], "new_plan": "x", "claim_boundary": BOUNDARY}
        )


# --- advisory evidence is not permission -----------------------------------

def test_generalization_result_is_advisory_only():
    att = attach_advisory_evidence(goal_ref="goal-1", kind="generalization_result", refs=["gen-1"])
    assert att["advisory_only"] is True
    assert att["used_as_permission"] is False
    with pytest.raises(GoalLifecycleError, match="generalization_result_is_not_permission"):
        attach_advisory_evidence(goal_ref="goal-1", kind="generalization_result", refs=["gen-1"], as_permission=True)


def test_workbench_capability_is_not_permission():
    att = attach_advisory_evidence(goal_ref="goal-1", kind="workbench_capability", refs=["cap-1"])
    assert att["advisory_only"] is True
    with pytest.raises(GoalLifecycleError, match="workbench_capability_is_not_permission"):
        attach_advisory_evidence(goal_ref="goal-1", kind="workbench_capability", refs=["cap-1"], as_permission=True)


def test_memory_reference_is_not_permission():
    att = attach_advisory_evidence(goal_ref="goal-1", kind="memory_reference", refs=["mem-1"])
    assert att["advisory_only"] is True
    with pytest.raises(GoalLifecycleError, match="memory_reference_is_not_permission"):
        attach_advisory_evidence(goal_ref="goal-1", kind="memory_reference", refs=["mem-1"], as_permission=True)


# --- dry/live boundary -----------------------------------------------------

def test_dry_live_boundary_is_enforced():
    with pytest.raises(GoalLifecycleError, match="dry_live_boundary_enforced"):
        select_work_item(
            {
                "work_item_id": "wi-live",
                "candidate_task_ref": "t-1",
                "allowed_class_ref": "remediation",
                "authority_refs": ["gpp:1"],
                "receipt_plan": {"gate": "g"},
                "live": True,
                "permit_refs": [],
                "claim_boundary": BOUNDARY,
            }
        )


# --- schema violations -----------------------------------------------------

def test_schema_violation_blocks_success():
    with pytest.raises(GoalLifecycleError, match="schema_violation:missing"):
        create_candidate_task({"task_id": "t-x"})


# --- replay ----------------------------------------------------------------

def test_goal_replay_is_deterministic(tmp_path):
    log = GoalLifecycleLog(tmp_path / "goals.jsonl")
    log.append("goal_record_v1", {"goal_id": "goal-1", "state": ACTIVE})
    log.append("goal_state_transition_v1", {"goal_ref": "goal-1", "to_state": STOPPED})
    result = log.replay()
    assert result.ok is True
    assert result.records == 2


def test_replay_divergence_is_failure(tmp_path):
    path = tmp_path / "goals.jsonl"
    log = GoalLifecycleLog(path)
    log.append("goal_record_v1", {"goal_id": "goal-1", "state": ACTIVE})
    log.append("goal_state_transition_v1", {"goal_ref": "goal-1", "to_state": STOPPED})
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["payload"]["state"] = PANIC_HALTED
    lines[0] = json.dumps(tampered, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = GoalLifecycleLog(path).replay()
    assert result.ok is False
    assert any("payload_hash_mismatch" in e for e in result.errors)


def test_replay_under_panic_is_refused(tmp_path):
    log = GoalLifecycleLog(tmp_path / "goals.jsonl")
    log.append("goal_record_v1", {"goal_id": "goal-1", "state": ACTIVE})
    with pytest.raises(GoalLifecycleError):
        log.replay(control=PANIC)


# --- gate ------------------------------------------------------------------

def _green_gate_kwargs(**overrides):
    kwargs = dict(
        phase26_green=True,
        phase29_green=True,
        phase31_green=True,
        proof_bundle=Path("dummy"),
        tests_passed=True,
        report_exists=True,
        goals_cannot_grant_authority=True,
        goals_cannot_authorize_tools=True,
        goals_cannot_create_live_effects=True,
        candidate_tasks_are_not_execution=True,
        allowed_task_class_required_before_selection=True,
        ambiguous_intent_enters_ask_operator=True,
        stop_panic_halts_lifecycle=True,
        panic_blocks_task_selection=True,
        failed_receipts_preserved=True,
        replanning_preserves_failure_history=True,
        generalization_evidence_advisory_only=True,
        workbench_capability_advisory_only=True,
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


def test_phase32_gate_green_when_all_checks_pass(tmp_path):
    result = evaluate_phase32_gate(**_green_gate_kwargs(proof_bundle=_make_bundle(tmp_path)))
    assert result["verdict"] == "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_32_LONG_HORIZON_GOAL_LIFECYCLE"
    assert result["ok"] is True


def test_phase32_gate_refuses_without_phase26_phase29_phase31_green(tmp_path):
    bundle = _make_bundle(tmp_path)
    assert evaluate_phase32_gate(**_green_gate_kwargs(proof_bundle=bundle, phase26_green=False))["ok"] is False
    assert evaluate_phase32_gate(**_green_gate_kwargs(proof_bundle=bundle, phase29_green=False))["ok"] is False
    assert evaluate_phase32_gate(**_green_gate_kwargs(proof_bundle=bundle, phase31_green=False))["ok"] is False


def test_phase32_gate_refuses_without_proof_bundle():
    result = evaluate_phase32_gate(**_green_gate_kwargs(proof_bundle=None))
    assert result["ok"] is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in result["failures"])


def test_proof_bundle_validator_flags_missing_files(tmp_path):
    ok, failures = validate_phase32_proof_bundle(tmp_path)
    assert ok is False
    assert failures
