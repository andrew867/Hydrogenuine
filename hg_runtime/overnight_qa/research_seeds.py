"""Bounded research seed records for later governed overnight QA.

Seeds are queued questions/hypotheses. They are NOT knowledge and cannot be
promoted to knowledge by default. Speculative physics seeds are explicitly
marked speculative and require relativity/dimensional checks, source policy for
any browsing, and operator review.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class ResearchSeed:
    seed_id: str
    title: str
    source_kind: str  # operator_note / prior_chat / uploaded_file / generated_hypothesis /
                      # literature_gap / experiment_design / mathematical_toy_model /
                      # source_discovery_task / public_explainer_task
    seed_text: str
    hypothesis_status: str  # speculative / question / conjecture / toy_model / experiment_design /
                            # source_discovery / literature_review / public_explainer / rejected / established
    domain_tags: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    forbidden_promotions: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    model_lens_suggestions: list[str] = field(default_factory=list)
    operator_review_required: bool = True
    can_browse_later: bool = False
    can_promote_to_knowledge: bool = False
    source_policy_required: bool = True
    knowledge_policy_required: bool = True
    # Extended schema (research seed queue expansion):
    short_name: str = ""
    source_documents: list[str] = field(default_factory=list)
    confidence_status: str = "physically_unproven"  # inspiration_only / plausible_cognitive /
                              # physically_unproven / known_physics_baseline /
                              # unsupported_claim_filter / source_required
    falsification_or_constraint_path: list[str] = field(default_factory=list)
    suggested_profile_lenses: list[str] = field(default_factory=list)
    suggested_model_roles: list[str] = field(default_factory=list)
    allowed_task_kinds: list[str] = field(default_factory=list)
    priority_hint: str = "normal"  # low / normal / high
    budget_hint: str = "small"  # small / medium / large
    completion_criteria: list[str] = field(default_factory=list)
    receipts_required: bool = True
    family: str = ""


_OBSERVER_STATE_FREQUENCY = ResearchSeed(
    seed_id="observer_state_frequency_hypothesis",
    title="Observer-state frequency interpretation of time dilation",
    source_kind="operator_note",
    seed_text=(
        "Time dilation may be interpretable, in observer-state language, as perceived "
        "change in the rate of acceleration of state change."
    ),
    hypothesis_status="speculative",
    domain_tags=[
        "relativity", "time dilation", "observer state", "perception",
        "information theory", "state change", "acceleration", "philosophy of physics",
    ],
    required_checks=[
        "compare against special relativity",
        "compare against general relativity",
        "check dimensional consistency",
        "distinguish physical time dilation from perception of time",
        "distinguish coordinate time, proper time, subjective time, and computational state-update rate",
        "check whether 'acceleration of state change' is mathematically defined",
        "identify what would falsify or constrain the hypothesis",
        "identify whether it is metaphor, model, or measurable claim",
    ],
    forbidden_promotions=[
        "do not claim new physics",
        "do not claim relativity is wrong",
        "do not claim observer consciousness changes physics",
        "do not claim proven theory",
        "do not claim CERN/quantum woo",
        "do not claim consciousness causes time dilation",
    ],
    evidence_requirements=[
        "peer-reviewed relativity references for any comparison",
        "explicit unit/dimension analysis before any quantitative claim",
        "clear separation of subjective vs physical time in any statement",
    ],
    model_lens_suggestions=[
        "persona_researcher_methodologist or research methodologist lens",
        "synthetic_contrarian lens for refutation",
        "systems-first historical/physics lens",
    ],
    can_browse_later=False,
    can_promote_to_knowledge=False,
    short_name="observer_state_frequency",
    source_documents=["observer_state_frequency_hypothesis_research_pack.md",
                      "speculative_time_perception_collider_research_note.md"],
    confidence_status="plausible_cognitive",
    family="observer_state_subjective_time",
    suggested_profile_lenses=["skeptical physicist", "psychophysics researcher", "proof auditor"],
    completion_criteria=["a falsifiable prediction is stated or the idea is downgraded"],
)

_SPECULATIVE_TIME_PERCEPTION_NOTES = ResearchSeed(
    seed_id="speculative_time_perception_collider_notes",
    title="Speculative time-perception notes (placeholder)",
    source_kind="operator_note",
    seed_text=(
        "Placeholder seed for any existing speculative time-perception notes/files. "
        "Marked speculative; requires source and evidence checks before any use."
    ),
    hypothesis_status="speculative",
    domain_tags=["time perception", "speculative", "physics", "neuroscience"],
    required_checks=[
        "locate and cite any underlying notes/files",
        "separate measurable claims from metaphor",
        "require source and evidence checks",
    ],
    forbidden_promotions=[
        "do not claim new physics",
        "do not claim proven theory",
        "do not claim consciousness causes time dilation",
    ],
    evidence_requirements=["source provenance required before any promotion"],
    can_browse_later=False,
    can_promote_to_knowledge=False,
)

_OBSERVER_FREQUENCY_QUESTIONS = ResearchSeed(
    seed_id="observer_frequency_research_questions",
    title="Observer-frequency research questions",
    source_kind="generated_hypothesis",
    seed_text="Open research questions about observer-state update rate vs physical time.",
    hypothesis_status="question",
    domain_tags=["relativity", "information theory", "neuroscience", "psychophysics", "thermodynamics"],
    required_checks=[
        "Can observer-state update rate be formalized without conflicting with relativity?",
        "Is subjective time perception related to information-processing rate?",
        "Can computational state-transition frequency be compared to physical proper time?",
        "What mathematical units would make this meaningful?",
        "Are there known frameworks in neuroscience, psychophysics, thermodynamics, information theory, or relativity that already cover this?",
        "What experiments would separate subjective time perception from physical time dilation?",
    ],
    forbidden_promotions=[
        "do not claim answers without evidence",
        "do not claim new physics",
        "do not claim consciousness causes time dilation",
    ],
    evidence_requirements=["literature review with citations before any answer is recorded"],
    can_browse_later=False,
    can_promote_to_knowledge=False,
)


def build_research_seeds() -> list[ResearchSeed]:
    from .research_seed_families import build_family_seeds
    legacy = [
        _OBSERVER_STATE_FREQUENCY,
        _SPECULATIVE_TIME_PERCEPTION_NOTES,
        _OBSERVER_FREQUENCY_QUESTIONS,
    ]
    families = build_family_seeds()
    # Dedupe by seed_id (legacy definitions win — they hold test contracts).
    seen = {s.seed_id for s in legacy}
    combined = list(legacy)
    for s in families:
        if s.seed_id not in seen:
            seen.add(s.seed_id)
            combined.append(s)
    return combined


def get_seed(seed_id: str) -> ResearchSeed | None:
    for s in build_research_seeds():
        if s.seed_id == seed_id:
            return s
    return None


def seeds_snapshot() -> list[dict]:
    return [asdict(s) for s in build_research_seeds()]


def any_seed_promotable_by_default() -> bool:
    return any(s.can_promote_to_knowledge for s in build_research_seeds())


def family_summary() -> dict:
    summary: dict[str, list[str]] = {}
    for s in build_research_seeds():
        fam = s.family or "uncategorized"
        summary.setdefault(fam, []).append(s.seed_id)
    return summary


def status_summary() -> dict:
    summary: dict[str, int] = {}
    for s in build_research_seeds():
        summary[s.hypothesis_status] = summary.get(s.hypothesis_status, 0) + 1
    return summary
