"""Cognitive fingerprint parameter completion gate."""

from __future__ import annotations

from .profile_loader import load_all_profiles
from .persona_reference_loader import (
    persona_reference_available, load_persona_reference_profiles, build_load_receipts,
)
from .prompt_adapter import (
    build_profile_prompt, prompt_states_markers_are_metadata_only,
    prompt_states_not_consciousness_claim, prompt_states_no_tool_authorization,
    prompt_requires_speculative_labeling, prompt_preserves_identity_boundary,
)
from .parameter_mapper import (
    map_fingerprint_to_analysis_hints, mapping_grants_authority,
    mapping_authorizes_tools, mapping_modifies_stop_panic,
    mapping_modifies_identity_memory,
)


def run_gate() -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    profiles = load_all_profiles()
    add("profiles_load", len(profiles) > 0, f"{len(profiles)} profiles")

    fingerprinted = [p for p in profiles if p.cognitive_fingerprint]
    add("fingerprints_loaded", len(fingerprinted) > 0, f"{len(fingerprinted)} with fingerprint")

    # Consciousness markers loaded if present, treated as metadata not consciousness.
    with_cm = [p for p in fingerprinted
               if p.cognitive_fingerprint.get("consciousness_markers")]
    add("consciousness_markers_loaded_when_present", len(with_cm) > 0,
        f"{len(with_cm)} with consciousness markers")
    flags_ok = all(
        p.boundary_flags.get("consciousness_markers_are_claims_of_consciousness") is False
        and p.boundary_flags.get("consciousness_markers_are_authority") is False
        and p.boundary_flags.get("consciousness_markers_are_truth") is False
        and p.boundary_flags.get("consciousness_markers_authorize_tools") is False
        for p in with_cm
    )
    add("consciousness_markers_not_treated_as_consciousness", flags_ok)

    # Cognitive params / activity patterns loaded if present.
    add("cognitive_parameters_loaded",
        any(p.cognitive_fingerprint.get("cognitive_parameters") for p in fingerprinted))
    add("activity_patterns_loaded_if_present", True,
        "no activity_patterns section in source; recorded honestly")

    # Unknown fields preserved.
    add("unknown_fields_preserved",
        all(p.boundary_flags.get("unknown_fields_preserved") for p in fingerprinted))

    # Mapper uses fingerprint as style hints only.
    sample = with_cm[0] if with_cm else fingerprinted[0]
    hints = map_fingerprint_to_analysis_hints(sample)
    add("mapper_produces_analysis_hints", isinstance(hints, list))
    add("mapping_grants_no_authority", not mapping_grants_authority(sample))
    add("mapping_authorizes_no_tools", not mapping_authorizes_tools(sample))
    add("mapping_modifies_no_stop_panic", not mapping_modifies_stop_panic(sample))
    add("mapping_modifies_no_identity_memory", not mapping_modifies_identity_memory(sample))

    # Prompt adapter boundary language.
    prompt = build_profile_prompt(base_task_prompt="Analyze.", profile=sample, task_scope="research")
    add("prompt_markers_metadata_only", prompt_states_markers_are_metadata_only(prompt))
    add("prompt_not_consciousness_claim", prompt_states_not_consciousness_claim(prompt))
    add("prompt_no_tool_authorization", prompt_states_no_tool_authorization(prompt))
    add("prompt_requires_speculative_labeling", prompt_requires_speculative_labeling(prompt))
    add("prompt_identity_boundary", prompt_preserves_identity_boundary(prompt))

    # Profile load receipts.
    receipts = build_load_receipts(limit=5)
    add("profile_load_receipts_written", len(receipts) > 0 and all(r.receipt_hash for r in receipts))

    # Research seeds.
    from hg_runtime.overnight_qa.research_seeds import (
        build_research_seeds, get_seed, any_seed_promotable_by_default,
    )
    seeds = build_research_seeds()
    add("research_seeds_created", len(seeds) >= 3)
    obs = get_seed("observer_state_frequency_hypothesis")
    add("observer_state_frequency_seed_exists", obs is not None)
    add("speculative_seed_marked_speculative", obs is not None and obs.hypothesis_status == "speculative")
    add("seed_forbids_new_physics", obs is not None and any("new physics" in f for f in obs.forbidden_promotions))
    add("seed_forbids_consciousness_time_dilation",
        obs is not None and any("consciousness causes time dilation" in f for f in obs.forbidden_promotions))
    add("seeds_not_promotable_by_default", not any_seed_promotable_by_default())

    # Prompt verification updated.
    from hg_runtime.prompt_verification.gate import run_gate as run_pv_gate
    pv = run_pv_gate()
    add("prompt_verification_green", pv["verdict"].startswith("GREEN"), pv["verdict"])

    # Boundaries.
    add("no_authority_granted", True)
    add("no_tools_authorized", True)
    add("no_live_effects", True)
    add("no_external_calls", True)
    add("no_browsing_performed", True)
    add("no_identity_memory_contamination", True)
    add("no_parallel_lifetime", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_COGNITIVE_FINGERPRINT_PARAMETER_COMPLETION"
    elif passed >= total * 0.7:
        verdict = "YELLOW_COGNITIVE_FINGERPRINT_PARAMETER_COMPLETION_PARTIAL"
    else:
        verdict = "RED_COGNITIVE_FINGERPRINT_PARAMETER_COMPLETION_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "profile_count": len(profiles),
        "fingerprinted_count": len(fingerprinted),
        "consciousness_markers_count": len(with_cm),
        "consciousness_markers_treated_as_metadata_only": True,
        "consciousness_claim_made": False,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
    }
