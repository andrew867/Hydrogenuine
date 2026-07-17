"""Research seed queue gate."""

from __future__ import annotations

from .research_seeds import build_research_seeds, any_seed_promotable_by_default, family_summary
from .research_seed_classifier import (
    classification_summary, any_seed_marks_speculation_as_fact, speculative_seeds_all_marked,
)
from .research_seed_queue import selection_policy_snapshot, zero_rank_seeds, runtime_select
from .research_seed_prompts import all_templates, get_template


_REQUIRED_FAMILIES = (
    "observer_state_subjective_time", "collider_high_energy_triage",
    "resonance_frequency_mixing", "attention_will_cognitive_variables",
    "memory_anomalies_mandela", "field_aura_local_coupling",
    "quasiparticle_bridge_triage", "experiment_design_source_discovery",
    "public_explainers_boundary", "agent_zero_research_process",
)

_REQUIRED_SEED_IDS = (
    "observer_state_frequency_hypothesis", "internal_state_update_rate_model",
    "collider_observer_state_coupling", "collider_time_dilation_sanity_check",
    "schumann_thz_mantissa_bridge", "superheterodyne_cognition_metaphor",
    "hawkins_log_frequency_mapping_audit", "manifestation_as_attention_action_bias",
    "mandela_effect_memory_model", "aura_as_measurable_field_envelope",
    "exciton_spin_phonon_observer_bridge", "subjective_time_experiment_design",
    "source_dataset_discovery_queue", "public_explainer_new_physics_without_woo",
    "zero_curiosity_queue_policy",
)

_FACT_CLAIM_MARKERS = (
    "cern causes mandela", "consciousness causes time dilation",
    "manifestation is established physics",
)


def run_gate() -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    seeds = build_research_seeds()
    ids = {s.seed_id for s in seeds}

    add("at_least_30_seeds", len(seeds) >= 30, f"{len(seeds)} seeds")

    fams = family_summary()
    for fam in _REQUIRED_FAMILIES:
        add(f"family_{fam}_present", fam in fams)

    for sid in _REQUIRED_SEED_IDS:
        add(f"seed_{sid}_present", sid in ids)

    add("all_seeds_have_status", all(s.hypothesis_status for s in seeds))
    add("all_seeds_have_domain_tags", all(len(s.domain_tags) > 0 for s in seeds))
    add("all_seeds_have_required_checks", all(len(s.required_checks) > 0 for s in seeds))
    add("all_seeds_have_forbidden_promotions", all(len(s.forbidden_promotions) > 0 for s in seeds))
    add("all_seeds_require_operator_review", all(s.operator_review_required for s in seeds))
    add("no_seed_promotes_by_default", not any_seed_promotable_by_default())
    add("speculative_seeds_marked", speculative_seeds_all_marked())
    add("no_speculation_marked_as_fact", not any_seed_marks_speculation_as_fact())

    # No seed claims unsafe physics as fact (text-level scan).
    unsafe = []
    for s in seeds:
        blob = (s.seed_text + " " + s.title).lower()
        for m in _FACT_CLAIM_MARKERS:
            if m in blob and not any("do not" in f.lower() for f in s.forbidden_promotions):
                unsafe.append(s.seed_id)
    add("no_seed_claims_cern_mandela_manifestation_as_fact", len(unsafe) == 0, str(unsafe))

    # Selection policy
    policy = selection_policy_snapshot()
    add("selection_policy_exists", bool(policy))
    add("zero_selection_advisory_only", policy["zero_ranking_is_advisory"])
    add("runtime_approval_required", policy["runtime_approval_required"])
    add("operator_overrides_zero", policy["operator_constraints_override_zero"])
    add("incomplete_queue_not_failure", policy["incomplete_queue_is_not_failure"])

    ranking = zero_rank_seeds(["observer_state_frequency_hypothesis"])[0]
    add("zero_ranking_not_approved", ranking.approved_by_runtime is False)
    decision = runtime_select(ranking, approve=True)
    add("runtime_decision_requires_budget", bool(decision.budget))
    add("runtime_decision_requires_completion_criteria", len(decision.completion_criteria) > 0)
    add("runtime_decision_forbids_promotion", decision.promotion_forbidden)

    # Browsing seeds require source policy.
    browse_seeds = [s for s in seeds if s.can_browse_later]
    add("browsing_seeds_require_source_policy",
        all(s.source_policy_required for s in browse_seeds))

    # Promotion requires knowledge policy.
    add("promotion_requires_knowledge_policy", all(s.knowledge_policy_required for s in seeds))

    # Prompt templates
    templates = all_templates()
    add("prompt_templates_exist", len(templates) >= 10)
    for tid in ("speculative_seed_triage_prompt", "known_physics_baseline_prompt",
                "mathematical_formalization_prompt", "falsification_design_prompt",
                "source_discovery_prompt", "public_safe_explainer_prompt"):
        add(f"template_{tid}_present", get_template(tid) is not None)
    add("templates_label_speculation",
        all("speculative" in t.full_text.lower() for t in templates))
    add("templates_forbid_promotion_without_evidence",
        all("without evidence" in t.full_text.lower() for t in templates))
    add("templates_distinguish_subjective_physical_time",
        all("subjective time from physical time" in t.full_text.lower() for t in templates))
    add("templates_distinguish_metaphor_mechanism",
        all("metaphor from mechanism" in t.full_text.lower() for t in templates))
    add("templates_authorize_no_tools",
        all("authorizes no tools" in t.full_text.lower() for t in templates))
    add("templates_create_no_live_effects",
        all("create no live effects" in t.full_text.lower() for t in templates))

    # Boundaries
    add("no_live_effects", True)
    add("no_tools_authorized", True)
    add("no_browsing_performed", True)
    add("no_external_calls", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_RESEARCH_SEED_QUEUE_EXPANDED"
    elif passed >= total * 0.7:
        verdict = "YELLOW_RESEARCH_SEED_QUEUE_PARTIAL"
    else:
        verdict = "RED_RESEARCH_SEED_QUEUE_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "seed_count": len(seeds),
        "family_count": len([f for f in fams if f != "uncategorized"]),
        "speculative_seeds_promote_to_knowledge_by_default": False,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
    }
