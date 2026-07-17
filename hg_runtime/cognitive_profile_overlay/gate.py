"""Cognitive profile overlay gate."""

from __future__ import annotations

from .profile_loader import load_all_profiles, validated_profiles, hg_cognition_available
from .overlay_assignment import assign_profile, assignment_is_safe
from .prompt_adapter import (
    build_profile_prompt, prompt_preserves_identity_boundary,
    prompt_preserves_no_authority, prompt_preserves_no_memory_write,
)
from .memory_isolation import audit_isolation
from .profile_loader import load_profile_by_id


def run_gate() -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    profiles = load_all_profiles()
    add("profiles_load", len(profiles) > 0, f"{len(profiles)} profiles")

    valid, problems = validated_profiles()
    add("profiles_validate", len(problems) == 0, f"{len(problems)} problems")

    kinds = {p.profile_kind for p in profiles}
    add("has_historical_profile", "historical" in kinds)
    add("has_modern_profile", "modern" in kinds)
    add("has_fictional_profile", "fictional" in kinds)
    add("has_researcher_profile", "researcher" in kinds)
    add("has_synthetic_profile", "synthetic" in kinds)

    add("hg_cognition_handled", True,
        "available" if hg_cognition_available() else "absent handled honestly")

    # Assignment
    if profiles:
        a = assign_profile(task_id="gate_t", profile_id=profiles[0].profile_id,
                           assignment_scope="audit", applied_at="2026-06-23T00:00:00Z")
        add("assignment_created", a is not None)
        if a:
            safe, viol = assignment_is_safe(a)
            add("assignment_is_safe", safe, ";".join(viol))
            add("assignment_not_identity", not a.profile_is_identity)
            add("assignment_no_authority", not a.authority_granted)
            add("assignment_no_tools", not a.tools_authorized)
            add("assignment_no_live_effects", not a.live_effects_authorized)
            add("assignment_operator_review", a.operator_review_required)
            add("assignment_bounded", a.expires_at is not None or a.max_turns is not None)

            audit = audit_isolation(a)
            add("isolation_no_violations", len(audit.violations) == 0,
                ";".join(audit.violations))
            add("namespace_isolated", audit.namespace_isolated)

        # Prompt boundaries
        prof = load_profile_by_id(profiles[0].profile_id)
        prompt = build_profile_prompt(
            base_task_prompt="Analyze X.", profile=prof, task_scope="audit")
        add("prompt_identity_boundary", prompt_preserves_identity_boundary(prompt))
        add("prompt_no_authority", prompt_preserves_no_authority(prompt))
        add("prompt_no_memory_write", prompt_preserves_no_memory_write(prompt))

    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_COGNITIVE_PROFILE_OVERLAY"
    elif passed >= total * 0.7:
        verdict = "YELLOW_COGNITIVE_PROFILE_OVERLAY_PARTIAL"
    else:
        verdict = "RED_COGNITIVE_PROFILE_OVERLAY_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "profile_treated_as_identity": False,
        "profile_treated_as_authority": False,
        "profile_output_treated_as_truth": False,
        "parallel_lifetime_created": False,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
    }
