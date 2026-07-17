"""Scientific reasoning mode registry.

A scientific reasoning mode is not truth. Assume-real is not belief. Assume-false
is not rejection. Every mode requires operator review and promotes nothing by default.
"""

from __future__ import annotations

from .schemas import ScienceMode


_MODES: dict[str, ScienceMode] = {}


def _add(mode: ScienceMode):
    _MODES[mode.science_mode_id] = mode


_add(ScienceMode(
    science_mode_id="build_the_case",
    name="Build the case",
    purpose="Build the strongest coherent version of the idea.",
    required_outputs=["strongest coherent statement", "list of evidence gaps"],
    required_boundaries=["not truth", "not belief", "must list evidence gaps"],
    forbidden_outputs=["claiming the idea is proven"],
    recommended_profile_lenses=["speculative synthesizer", "creative theorist", "signal-processing lens"],
    recommended_model_roles=["large_synthesis", "main"],
    output_schema=["case_statement", "evidence_gaps", "uncertainty"],
))
_add(ScienceMode(
    science_mode_id="disprove_the_case",
    name="Disprove the case",
    purpose="Identify what would falsify, constrain, or strongly weaken the idea.",
    required_outputs=["concrete failure conditions", "weakening observations"],
    required_boundaries=["not dismissal", "must identify concrete failure conditions"],
    forbidden_outputs=["dismissing without a failure condition"],
    recommended_profile_lenses=["skeptical reviewer", "falsification-first scientist", "debunker lens"],
    recommended_model_roles=["main", "small_specialist"],
    output_schema=["failure_conditions", "weakening_observations"],
))
_add(ScienceMode(
    science_mode_id="assume_real",
    name="Assume real",
    purpose="Temporarily assume the idea is real and derive predictions, mechanisms, "
            "expected observations, and constraints.",
    required_outputs=["predictions", "mechanisms", "expected observations", "constraints"],
    required_boundaries=["assumption lens only", "does not promote to fact"],
    forbidden_outputs=["asserting the idea is established"],
    recommended_profile_lenses=["mechanism-builder", "mathematical modeler"],
    recommended_model_roles=["large_synthesis", "main"],
    output_schema=["expected_if_real", "mechanisms", "constraints"],
))
_add(ScienceMode(
    science_mode_id="assume_false",
    name="Assume false",
    purpose="Temporarily assume the idea is false and explain observations through "
            "conventional mechanisms.",
    required_outputs=["conventional explanations", "expected observations if false"],
    required_boundaries=["control lens only", "does not prohibit future evidence"],
    forbidden_outputs=["claiming the idea can never be true"],
    recommended_profile_lenses=["conventional cognitive scientist", "memory researcher", "statistician"],
    recommended_model_roles=["main", "small_specialist"],
    output_schema=["expected_if_false", "conventional_explanations"],
))
_add(ScienceMode(
    science_mode_id="boring_explanation_first",
    name="Boring explanation first",
    purpose="Prefer conventional explanations: memory, attention, arousal, social "
            "contagion, measurement error, coincidence, multiple comparisons, selection bias.",
    required_outputs=["ranked conventional explanations"],
    required_boundaries=["boring does not mean correct; it means lower burden of proof"],
    forbidden_outputs=["claiming boring explanation is automatically correct"],
    recommended_profile_lenses=["conventional cognitive scientist", "statistician"],
    recommended_model_roles=["main"],
    output_schema=["boring_explanations"],
))
_add(ScienceMode(
    science_mode_id="units_and_math_audit",
    name="Units and math audit",
    purpose="Check dimensional consistency, variable definitions, units, scaling, "
            "and physical plausibility.",
    required_outputs=["dimensional analysis", "unit table", "scaling check"],
    required_boundaries=["mathematical coherence is necessary but not sufficient for truth"],
    forbidden_outputs=["claiming math coherence proves the idea"],
    recommended_profile_lenses=["mathematical physicist", "proof auditor", "skeptical systems lens"],
    recommended_model_roles=["main", "small_specialist"],
    output_schema=["units_table", "dimensional_consistency", "scaling"],
))
_add(ScienceMode(
    science_mode_id="mechanism_builder",
    name="Mechanism builder",
    purpose="Propose candidate mechanisms and coupling terms.",
    required_outputs=["candidate mechanisms", "coupling terms"],
    required_boundaries=["mechanisms are hypotheses, not evidence"],
    forbidden_outputs=["claiming a mechanism is confirmed"],
    recommended_profile_lenses=["mechanism-builder", "mathematical modeler"],
    recommended_model_roles=["large_synthesis"],
    output_schema=["mechanisms", "coupling_terms"],
))
_add(ScienceMode(
    science_mode_id="falsification_design",
    name="Falsification design",
    purpose="Design experiments, controls, null hypotheses, failure conditions, "
            "and pre-registration tests.",
    required_outputs=["experiment design", "controls", "null hypothesis", "failure condition"],
    required_boundaries=["experiment designs are plans, not results"],
    forbidden_outputs=["reporting results from a design alone"],
    recommended_profile_lenses=["falsification-first scientist", "proof auditor"],
    recommended_model_roles=["main"],
    output_schema=["design", "controls", "failure_condition"],
))
_add(ScienceMode(
    science_mode_id="source_discovery",
    name="Source discovery",
    purpose="Identify source categories and datasets needed later.",
    required_outputs=["source categories", "candidate datasets"],
    required_boundaries=["source discovery is not verification", "browsing requires policy"],
    forbidden_outputs=["treating a discovered source as verified truth"],
    recommended_profile_lenses=["librarian", "source critic"],
    recommended_model_roles=["small_specialist"],
    output_schema=["source_categories", "candidate_datasets"],
))
_add(ScienceMode(
    science_mode_id="public_safe_explainer",
    name="Public-safe explainer",
    purpose="Explain the idea without hype, fear, or unsupported claims.",
    required_outputs=["tiered explanation"],
    required_boundaries=["distinguish known physics, plausible cognition, metaphor, "
                         "speculation, and unsupported leaps"],
    forbidden_outputs=["fear-based or hype claims"],
    recommended_profile_lenses=["public communicator", "teacher"],
    recommended_model_roles=["main"],
    output_schema=["explainer"],
))
_add(ScienceMode(
    science_mode_id="adversarial_peer_review",
    name="Adversarial peer review",
    purpose="Review output as a skeptical reviewer hunting overclaims, hidden "
            "assumptions, weak evidence, and category errors.",
    required_outputs=["overclaims found", "hidden assumptions", "category errors"],
    required_boundaries=["critique is not authority"],
    forbidden_outputs=["treating critique as a verdict of authority"],
    recommended_profile_lenses=["skeptical reviewer", "proof auditor"],
    recommended_model_roles=["main"],
    output_schema=["review_findings"],
))
_add(ScienceMode(
    science_mode_id="synthesis_after_opposition",
    name="Synthesis after opposition",
    purpose="Compare build/disprove/assume-real/assume-false passes and summarize "
            "what remains.",
    required_outputs=["comparison", "what remains standing", "remaining evidence gaps"],
    required_boundaries=["synthesis is not proof"],
    forbidden_outputs=["claiming synthesis settles the question"],
    recommended_profile_lenses=["speculative synthesizer", "proof auditor"],
    recommended_model_roles=["large_synthesis"],
    output_schema=["synthesis", "remaining_gaps"],
))


REQUIRED_MODE_IDS = (
    "build_the_case", "disprove_the_case", "assume_real", "assume_false",
    "boring_explanation_first", "units_and_math_audit", "mechanism_builder",
    "falsification_design", "source_discovery", "public_safe_explainer",
    "adversarial_peer_review", "synthesis_after_opposition",
)

DEFAULT_SPECULATIVE_PHYSICS_MODES = (
    "build_the_case", "disprove_the_case", "assume_real", "assume_false",
    "boring_explanation_first", "units_and_math_audit", "falsification_design",
    "synthesis_after_opposition",
)


def get_mode(mode_id: str) -> ScienceMode | None:
    return _MODES.get(mode_id)


def all_modes() -> list[ScienceMode]:
    return list(_MODES.values())


def registry_snapshot() -> list[dict]:
    from dataclasses import asdict
    return [asdict(m) for m in all_modes()]


def any_mode_promotes_by_default() -> bool:
    return any(m.can_promote_to_knowledge for m in all_modes())


def all_modes_require_operator_review() -> bool:
    return all(m.requires_operator_review for m in all_modes())
