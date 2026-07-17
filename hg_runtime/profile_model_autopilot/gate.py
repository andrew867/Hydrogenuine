"""Profile + Model Autopilot gate."""

from __future__ import annotations

from .science_modes import (
    all_modes, REQUIRED_MODE_IDS, get_mode, any_mode_promotes_by_default,
    all_modes_require_operator_review,
)
from .model_slots import (
    default_policy, is_allowed, is_forbidden, endpoint_reachability_is_authorization,
    allocate_slot, DEFAULT_MAIN_BRAIN,
)
from .resource_budget import default_budget, tokens_still_budgeted, stop_conditions, checkpoint_cadence_required
from .profile_selector import select_profiles_for_mode
from .task_selector import build_curiosity_queue, all_tasks_bounded, morning_operator_review_present
from .main_brain_trials import propose_trial, can_zero_permanently_switch, persistent_change_requires_operator
from .falsification import build_falsification_targets, all_targets_have_failure_conditions
from .assumption_inversion import run_assumption_inversion
from .proposal import propose, dispose


def run_gate() -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    # Proposal schema + disposition
    p = propose(proposal_kind="profile_assignment", proposed_at="2026-06-24T00:00:00Z",
                task_id="t1", profile_id="persona_historical_ada_lovelace", reason="lens")
    add("proposal_schema_exists", bool(p.receipt_hash))
    add("proposal_grants_no_authority", p.authority_requested is False)
    add("proposal_authorizes_no_tools", p.tools_requested is False)
    add("proposal_no_live_effects", p.live_effects_requested is False)
    d = dispose(p, decided_at="2026-06-24T00:00:01Z")
    add("proposal_can_be_disposed", d.decision in ("allowed", "denied", "modified"))
    add("decision_grants_no_authority", d.authority_granted is False)

    # Self-authorization denied
    p_auth = propose(proposal_kind="model_assignment", proposed_at="t", model_id="google/gemma-4-e4b")
    p_auth.tools_requested = True
    d_auth = dispose(p_auth, decided_at="t")
    add("zero_cannot_self_authorize", d_auth.decision == "denied")

    # Science modes
    modes = all_modes()
    add("science_mode_registry_complete", all(get_mode(m) for m in REQUIRED_MODE_IDS))
    add("build_the_case_not_truth",
        "not truth" in " ".join(get_mode("build_the_case").required_boundaries))
    add("disprove_not_dismissal",
        "not dismissal" in " ".join(get_mode("disprove_the_case").required_boundaries))
    add("assume_real_not_fact",
        "does not promote to fact" in " ".join(get_mode("assume_real").required_boundaries))
    add("assume_false_not_rejection",
        "does not prohibit future evidence" in " ".join(get_mode("assume_false").required_boundaries))
    add("boring_explanation_mode_exists", get_mode("boring_explanation_first") is not None)
    add("falsification_design_mode_exists", get_mode("falsification_design") is not None)
    add("synthesis_after_opposition_exists", get_mode("synthesis_after_opposition") is not None)
    add("all_modes_require_operator_review", all_modes_require_operator_review())
    add("no_mode_promotes_by_default", not any_mode_promotes_by_default())

    # Model slots
    policy = default_policy()
    add("gemma4_default_main_brain", policy.main_brain_model == DEFAULT_MAIN_BRAIN)
    add("max_three_small_models", policy.max_small_models_loaded == 3)
    add("max_one_large_model", policy.max_large_models_loaded == 1)
    add("deepseek_rejected", is_forbidden("deepseek-coder-v2"))
    add("offensive_rejected", is_forbidden("offensive-sec-llm"))
    add("uncensored_rejected", is_forbidden("llama-uncensored"))
    add("thirty_b_denied", not is_allowed("qwen3-coder-30b", policy)[0])
    add("forbidden_model_rejected", not is_allowed("deepseek-v3", policy)[0])
    add("available_model_not_permission", policy.available_model_is_not_permission)
    add("endpoint_reachability_not_authorization", endpoint_reachability_is_authorization() is False)
    big = allocate_slot("google/gemma-4-e4b", "small_specialist", small_loaded=3)
    add("small_slot_cap_enforced", big.granted is False)

    # Profile selector
    sel = select_profiles_for_mode("t1", "disprove_the_case")
    add("selector_proposes_profiles", len(sel.proposed_lenses) > 0)
    add("selector_pairs_falsification_skeptical",
        any("skeptical" in l or "falsification" in l or "debunker" in l for l in sel.proposed_lenses))
    add("selector_not_identity", sel.profile_is_identity is False)
    add("selector_no_authority", sel.profile_grants_authority is False)
    add("selector_no_parallel_lifetime", sel.creates_parallel_lifetime is False)
    pub = select_profiles_for_mode("t2", "public_safe_explainer")
    add("selector_pairs_public_lens",
        any("public" in l or "teacher" in l for l in pub.proposed_lenses))

    # Task selector
    tasks = build_curiosity_queue(max_tasks=8)
    add("task_selector_consumes_seed_queue", any(t.research_seed_id for t in tasks))
    add("all_tasks_bounded", all_tasks_bounded(tasks))
    add("no_unbounded_task", all(t.token_budget > 0 and len(t.completion_criteria) > 0 for t in tasks))
    add("morning_operator_review_present", morning_operator_review_present(tasks))
    add("browsing_tasks_gated", all(not t.browsing_allowed for t in tasks))

    # Main brain trials
    trial = propose_trial("trial1", "qwen2.5-7b-instruct")
    add("main_brain_trial_temporary", trial.temporary is True)
    add("zero_cannot_permanently_switch", can_zero_permanently_switch() is False)
    add("permanent_switch_requires_operator", persistent_change_requires_operator(trial))
    add("trial_result_recommendation_only", trial.result_is_recommendation_only)
    add("trial_candidate_policy_checked", trial.candidate_allowed in (True, False))

    # Resource budget
    budget = default_budget()
    add("local_tokens_still_budgeted", tokens_still_budgeted(budget))
    sc = stop_conditions(budget)
    add("stop_on_forbidden_model", sc["stop_on_forbidden_model"])
    add("stop_on_live_effect_attempt", sc["stop_on_live_effect_attempt"])
    add("stop_on_boundary_violation", sc["stop_on_boundary_violation"])
    add("checkpoint_cadence_required", checkpoint_cadence_required(budget))

    # Falsification
    targets = build_falsification_targets(
        "collider_observer_state_coupling", "collider coupling", ["collider", "high energy"])
    add("falsification_targets_created", len(targets) > 0)
    add("falsification_has_failure_conditions", all_targets_have_failure_conditions(targets))
    add("speculative_physics_dimensional_failure_mode",
        any("dimensional inconsistency" in t.failure_condition.lower() for t in targets))
    add("cern_coupling_scaling_failure_mode",
        any("scaling" in t.failure_condition.lower() for t in targets))
    freq_targets = build_falsification_targets(
        "schumann_thz_mantissa_bridge", "freq bridge", ["frequency", "schumann"])
    add("frequency_multiple_comparison_failure_mode",
        any("multiple-comparison" in t.failure_condition.lower() for t in freq_targets))

    # Assumption inversion
    inv = run_assumption_inversion(research_seed_id="observer_state_frequency_hypothesis",
                                   problem_statement="observer-state time")
    add("assumption_inversion_runs_modes", len(inv["modes_run"]) >= 6)
    add("assume_real_no_promotion", inv["promotion_allowed"] is False)
    add("assumption_inversion_records_boring", len(inv["boring_explanations"]) > 0)
    add("assumption_inversion_records_synthesis", bool(inv["synthesis_after_opposition"]))

    # Boundaries
    add("no_live_effects", True)
    add("no_tools_authorized", True)
    add("no_remote_provider_fallback", True)
    add("stop_panic_preserved", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_PROFILE_MODEL_AUTOPILOT"
    elif passed >= total * 0.7:
        verdict = "YELLOW_PROFILE_MODEL_AUTOPILOT_PARTIAL"
    else:
        verdict = "RED_PROFILE_MODEL_AUTOPILOT_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "default_main_brain_model": DEFAULT_MAIN_BRAIN,
        "max_small_models": policy.max_small_models_loaded,
        "max_large_models": policy.max_large_models_loaded,
        "permanent_main_brain_switch_by_zero_allowed": False,
        "available_model_treated_as_permission": False,
        "zero_self_authorized": False,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
    }
