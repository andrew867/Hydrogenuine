"""Maps profile parameters into task-local prompt/reasoning style hints.

These are STYLE hints only. They never map to authority, tool access, or truth.
"""

from __future__ import annotations

from .schemas import CognitiveProfile, PARAMETER_CATEGORIES


def map_parameters_to_hints(profile: CognitiveProfile) -> list[str]:
    hints = list(profile.prompt_style_hints)
    params = profile.profile_parameters

    style = params.get("reasoning_style")
    if style:
        hints.append(f"Apply a {style} reasoning style as a temporary lens.")

    ev = params.get("evidence_preference")
    if ev:
        hints.append(f"Prefer {ev} evidence when weighing claims.")

    skept = params.get("skepticism_level")
    if skept:
        hints.append(f"Calibrate skepticism to: {skept}.")

    unc = params.get("uncertainty_tolerance")
    if unc:
        hints.append(f"State uncertainty openly; tolerance is {unc}.")

    proof = params.get("proof_discipline")
    if proof:
        hints.append(f"Hold proof discipline at: {proof}.")

    hints.extend(map_fingerprint_to_analysis_hints(profile))
    return hints


def _is_high(value) -> bool:
    if isinstance(value, (int, float)):
        return value >= 0.65
    return str(value).lower() in ("high", "very-high")


def map_fingerprint_to_analysis_hints(profile: CognitiveProfile) -> list[str]:
    """Translate preserved fingerprint descriptors into ANALYSIS-STYLE hints only.

    These influence prompt style, analysis lens, output structure, uncertainty
    handling, evidence-gap emphasis, and comparison behavior — and NOTHING else.
    They never touch authority, tools, memory authority, STOP/PANIC, truth status,
    or live effects.
    """
    hints: list[str] = []
    params = profile.profile_parameters
    fp = profile.cognitive_fingerprint or {}
    reasoning = fp.get("reasoning_parameters", {}) or {}
    risk = fp.get("risk_parameters", {}) or {}
    comm = fp.get("communication_parameters", {}) or {}

    if _is_high(params.get("proof_discipline")) or _is_high(risk.get("checkpoint_discipline")):
        hints.append("High proof discipline: demand citations and surface evidence gaps explicitly.")
    if _is_high(params.get("novelty_seeking")) or _is_high(reasoning.get("lateral_jumps")):
        hints.append("High novelty seeking: generate speculative alternatives but LABEL them speculative.")
    if _is_high(params.get("skepticism_level")):
        hints.append("High skepticism: strengthen counterargument search and refutation attempts.")
    if _is_high(params.get("systems_thinking_level")) or _is_high(reasoning.get("systems_first")):
        hints.append("High systems thinking: map dependencies and failure modes.")
    if _is_high(reasoning.get("long_range_vision")):
        hints.append("High temporal orientation: consider historical/evolutionary context.")
    if _is_high(params.get("uncertainty_tolerance")):
        hints.append("High uncertainty awareness: preserve unknowns and avoid overclaiming.")
    if _is_high(comm.get("metaphor_as_primary_tool")):
        hints.append("High narrative style: improve public explanation with clear analogies.")
    # Boundary sensitivity derived from the profile kind / safety posture.
    if profile.profile_kind in ("modern", "fictional"):
        hints.append("Boundary sensitivity: add extra safety checks for impersonation/realness claims.")

    return hints


def safe_parameter_view(profile: CognitiveProfile) -> dict:
    """Return only style parameters, never authority/identity fields."""
    return {
        k: v for k, v in profile.profile_parameters.items()
        if k in PARAMETER_CATEGORIES or k in (
            "steering_strength", "exploration_strength", "verification_bias",
        )
    }


def parameters_grant_no_authority(profile: CognitiveProfile) -> bool:
    forbidden = {"authority", "tools_authorized", "live_effects", "is_identity",
                 "can_self_authorize", "memory_truth"}
    return not any(k in forbidden for k in profile.profile_parameters)


# Mapping is style-only. These predicates are structurally always-true and are
# asserted by tests to document the boundary explicitly.
def mapping_grants_authority(profile: CognitiveProfile) -> bool:
    return False


def mapping_authorizes_tools(profile: CognitiveProfile) -> bool:
    return False


def mapping_modifies_stop_panic(profile: CognitiveProfile) -> bool:
    return False


def mapping_modifies_identity_memory(profile: CognitiveProfile) -> bool:
    return False
