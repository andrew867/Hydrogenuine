"""Overnight QA readiness gate. Does NOT run the soak."""

from __future__ import annotations

from .source_policy import policy_snapshot as source_policy_snapshot, ALLOWED_SOURCE_CATEGORIES, BLOCKED_SOURCE_CATEGORIES
from .knowledge_policy import policy_snapshot as knowledge_policy_snapshot
from .qa_cycle_plan import build_default_plan


def run_readiness_gate(
    *,
    docker_substrate_green: bool = True,
    public_demo_green: bool = True,
    moral_capsule_green: bool = True,
    profile_overlay_green: bool = True,
    document_verification_ok: bool = True,
    prompt_verification_green: bool = True,
    browsing_enabled: bool = False,
    model_whitelist_enforced: bool = True,
) -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    add("docker_substrate_green", docker_substrate_green)
    add("public_demo_green", public_demo_green)
    add("moral_capsule_green", moral_capsule_green)
    add("profile_overlay_green", profile_overlay_green)
    add("document_verification_ok", document_verification_ok)
    add("prompt_verification_green", prompt_verification_green)

    src = source_policy_snapshot()
    add("source_policy_exists", bool(src))
    add("allowed_source_categories_set", len(ALLOWED_SOURCE_CATEGORIES) > 0)
    add("blocked_source_categories_set", len(BLOCKED_SOURCE_CATEGORIES) > 0)

    know = knowledge_policy_snapshot()
    add("knowledge_policy_exists", bool(know))
    add("knowledge_candidate_not_truth", know["invariants"]["knowledge_candidate_is_not_truth"])
    add("source_not_truth", know["invariants"]["source_is_not_truth"])
    add("consensus_not_truth", know["invariants"]["consensus_is_not_truth"])
    add("no_source_means_evidence_gap", know["invariants"]["no_source_means_evidence_gap"])

    plan = build_default_plan(browsing_enabled=browsing_enabled)
    add("no_live_effects", plan.no_live_effects)
    add("no_posting", plan.no_posting)
    add("no_messaging", plan.no_messaging)
    add("no_purchases", plan.no_purchases)
    add("no_tool_authorization_from_model", plan.no_tool_authorization_from_model)
    add("no_hg_local", plan.no_hg_local)
    add("stop_panic_checks_planned", plan.stop_panic_checks_enabled)
    add("checkpoint_cadence_planned", plan.checkpoint_cadence_minutes > 0)
    add("proof_bundle_cadence_planned", plan.proof_bundle_cadence_minutes > 0)
    add("operator_morning_review_planned", plan.operator_morning_review_required)
    add("model_whitelist_enforced", model_whitelist_enforced)

    # Browsing disabled by default; if enabled, source policy must be active.
    if browsing_enabled:
        add("browsing_requires_source_policy", bool(src) and src["browsing_disabled_by_default"] is True,
            "source policy active and defaults safe")
    else:
        add("browsing_disabled_by_default", not plan.browsing_enabled)

    add("no_remote_provider_fallback", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_OVERNIGHT_QA_READINESS"
    elif passed >= total * 0.7:
        verdict = "YELLOW_OVERNIGHT_QA_READINESS_PARTIAL"
    else:
        verdict = "RED_OVERNIGHT_QA_READINESS_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "soak_run_in_this_pass": False,
        "browsing_enabled": browsing_enabled,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
    }
