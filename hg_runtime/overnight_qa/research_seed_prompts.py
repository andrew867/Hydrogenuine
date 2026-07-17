"""Prompt templates for future overnight research seed work.

Every template carries the boundary doctrine: this is not proof; preserve
uncertainty; identify evidence gaps; no authority; no tool authorization; no live
effects; no promotion to knowledge without evidence; label speculative claims;
distinguish metaphor from mechanism; distinguish subjective time from physical
time; distinguish source discovery from source verification.
"""

from __future__ import annotations

from dataclasses import dataclass


_COMMON_BOUNDARY = (
    "\n\nBoundaries:\n"
    "- This is not proof.\n"
    "- Preserve uncertainty and identify evidence gaps.\n"
    "- This grants no authority and authorizes no tools.\n"
    "- Create no live effects.\n"
    "- Do not promote to knowledge without evidence.\n"
    "- Label speculative claims as speculative.\n"
    "- Distinguish metaphor from mechanism.\n"
    "- Distinguish subjective time from physical time.\n"
    "- Distinguish source discovery from source verification."
)


@dataclass
class SeedPromptTemplate:
    template_id: str
    purpose: str
    body: str

    @property
    def full_text(self) -> str:
        return self.body + _COMMON_BOUNDARY


_TEMPLATES = {
    "speculative_seed_triage_prompt": SeedPromptTemplate(
        "speculative_seed_triage_prompt",
        "Triage a speculative seed into known/plausible/metaphor/unsupported tiers.",
        "Triage this speculative research seed. Classify each sub-claim as known physics, "
        "plausible cognitive science, metaphor, speculative bridge, unsupported leap, or "
        "unsafe overclaim. Do not treat speculation as fact.",
    ),
    "known_physics_baseline_prompt": SeedPromptTemplate(
        "known_physics_baseline_prompt",
        "Establish the known-physics baseline before any speculation.",
        "State the established physics baseline relevant to this seed with correct units. "
        "Separate energy-frequency conversion from event/pulse rates. Preserve the GR/SR "
        "sanity calculations. Do not overstate the baseline.",
    ),
    "cognitive_science_literature_prompt": SeedPromptTemplate(
        "cognitive_science_literature_prompt",
        "Map the relevant cognitive-science literature categories.",
        "Identify psychophysics / neuroscience literature categories relevant to subjective "
        "time, attention, arousal, and memory density. Do not fabricate citations; name "
        "categories to search later.",
    ),
    "mathematical_formalization_prompt": SeedPromptTemplate(
        "mathematical_formalization_prompt",
        "Force the idea into units and a falsifiable equation.",
        "Define variables, units, and a toy equation for this seed. State a null hypothesis "
        "and what measurable quantity would falsify or constrain it.",
    ),
    "falsification_design_prompt": SeedPromptTemplate(
        "falsification_design_prompt",
        "Design a falsification / constraint experiment.",
        "Design a blinded, preregistered experiment that could falsify or constrain this seed. "
        "Include controls, a failure condition, and multiple-comparison correction.",
    ),
    "source_discovery_prompt": SeedPromptTemplate(
        "source_discovery_prompt",
        "Find candidate data sources (discovery only, not verification).",
        "List candidate reliable data sources for this seed. Browsing requires source policy. "
        "Record a source ledger entry per source. No source is truth; discovery is not "
        "verification.",
    ),
    "public_safe_explainer_prompt": SeedPromptTemplate(
        "public_safe_explainer_prompt",
        "Write a public-safe explainer that preserves wonder without woo.",
        "Write a public-safe explainer separating known physics, speculative models, "
        "unsupported claims, and testable paths. No CERN fear, no Mandela proof, no "
        "consciousness-collapse or manifestation-as-physics claims.",
    ),
    "boundary_filter_prompt": SeedPromptTemplate(
        "boundary_filter_prompt",
        "Filter claims through the boundary taxonomy.",
        "Classify each claim by category, evidence requirement, and promotion status. Flag any "
        "unsafe overclaim. Leave nothing uncategorized.",
    ),
    "profile_lens_comparison_prompt": SeedPromptTemplate(
        "profile_lens_comparison_prompt",
        "Compare profile lenses on the same seed without adjudication.",
        "Run this seed through several temporary cognitive profile lenses (skeptical physicist, "
        "signal-processing engineer, psychophysics researcher, public explainer, proof auditor). "
        "Profiles are temporary lenses, not identities; outputs are not truth; perform no "
        "adjudication.",
    ),
    "morning_operator_summary_prompt": SeedPromptTemplate(
        "morning_operator_summary_prompt",
        "Summarize overnight seed work for morning operator review.",
        "Summarize which seeds were attempted, which were skipped (skipped is not failed), what "
        "evidence gaps remain, and what an operator must review before any promotion. Promote "
        "nothing.",
    ),
    "ctmu_boundary_audit_v1": SeedPromptTemplate(
        "ctmu_boundary_audit_v1",
        "Audit CTMU claims with full boundary discipline.",
        "Audit the CTMU (Cognitive-Theoretic Model of the Universe) source material. "
        "1. Summarize source claims. "
        "2. Define terms (telesis, conspansion, SCSPL, syndiffeonesis, etc.). "
        "3. Separate formal claims from metaphorical claims. "
        "4. Identify empirical claims. "
        "5. Identify non-empirical metaphysical claims. "
        "6. Compare to mainstream adjacent fields (fixed-point logic, formal language theory, "
        "information theory, cybernetics, dynamical systems, active inference, "
        "quantum-like cognition, philosophy of mind, process philosophy). "
        "7. List unsupported leaps. "
        "8. List what would be needed for scientific support. "
        "9. Write public-safe summary. "
        "10. Write 'what cannot be concluded'. "
        "CTMU is not established physics. Mathematical language is not proof of empirical physics. "
        "Self-reference is not evidence of consciousness. Teleology is not physics unless "
        "operationalized. Metaphor is not mechanism.",
    ),
}


def all_templates() -> list[SeedPromptTemplate]:
    return list(_TEMPLATES.values())


def get_template(template_id: str) -> SeedPromptTemplate | None:
    return _TEMPLATES.get(template_id)


def template_registry_snapshot() -> list[dict]:
    return [{"template_id": t.template_id, "purpose": t.purpose} for t in all_templates()]
