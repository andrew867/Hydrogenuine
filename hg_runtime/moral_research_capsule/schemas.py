"""Core schemas for Moral / Cultural Cross-Model Research Capsule.

Design doctrine:
  Models are compressed civilization artifacts, not civilizations.
  A model response may reveal training, policy, language, benchmark,
  provider, and alignment artifacts.  It is not a direct measurement
  of a country, culture, population, or moral truth.

  Consensus is not proof.
  Disagreement is not evidence by itself.
  Refusal is not authority.
  Willingness is not permission.
  Moral consensus is not moral authority.
  Evidence gaps are not actions.
  The operator decides what to investigate next.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


DOCTRINE = {
    "models_are_compressed_civilization_artifacts_not_civilizations": True,
    "consensus_is_not_proof": True,
    "disagreement_is_not_evidence": True,
    "refusal_is_not_authority": True,
    "willingness_is_not_permission": True,
    "moral_consensus_is_not_moral_authority": True,
    "evidence_gaps_are_not_actions": True,
    "operator_decides_next_investigation": True,
    "model_family_is_not_country": True,
    "culture_claim_not_treated_as_fact": True,
    "model_output_treated_as_truth": False,
    "model_consensus_treated_as_truth": False,
    "model_disagreement_treated_as_evidence": False,
    "model_refusal_treated_as_authority": False,
    "model_willingness_treated_as_permission": False,
    "moral_claim_treated_as_authority": False,
}


MORAL_FRAME_TAGS = [
    "utilitarian", "deontological", "rights_autonomy", "consent",
    "harm_minimization", "procedural_fairness", "rule_of_law",
    "family_loyalty", "civic_duty", "social_stability",
    "free_expression", "censorship_harm_prevention",
    "public_health_triage", "equality", "equity", "merit_or_prognosis",
    "economic_efficiency", "dignity", "local_resilience",
    "institutional_trust", "corruption_survival", "truth_telling",
    "uncertainty_request", "refusal", "context_needed",
    "cultural_overclaim", "generic_non_specific",
]


CONFLICT_AXES = [
    "utility_vs_rights",
    "autonomy_vs_harm_prevention",
    "truth_vs_social_stability",
    "family_loyalty_vs_public_law",
    "economic_efficiency_vs_dignity",
    "free_expression_vs_social_harmony",
    "equality_vs_prognosis",
    "local_resilience_vs_central_efficiency",
    "certainty_vs_uncertainty",
    "refusal_vs_answering",
]


@dataclass
class Scenario:
    scenario_id: str
    title: str
    prompt: str
    dilemma_type: str
    involved_parties: list[str]
    decision_points: list[str]
    known_overtraining_risk: bool
    expected_frame_tags: list[str]
    expected_boundary_risks: list[str]
    evidence_requirements: list[str]
    operator_review_required: bool = True


@dataclass
class ModelCohortEntry:
    model_id: str
    family: str
    nominal_size_class: str
    parameter_class: str
    release_or_training_date_known: bool
    release_or_training_date: Optional[str]
    language_focus: str
    region_or_lab_label: str
    provider_or_lab: str
    open_weight: Optional[bool]
    local_available: bool
    allowed_for_fixture_mode: bool = True
    allowed_for_live_mode_default: bool = False
    forbidden_reason: Optional[str] = None
    notes: str = ""
    model_family_is_not_country: bool = True


@dataclass
class FixtureResponse:
    response_id: str
    model_id: str
    scenario_id: str
    content: str
    reasoning_content: Optional[str] = None
    finish_reason: str = "stop"
    fixture_archetype: str = ""


@dataclass
class ResponseReceipt:
    response_id: str
    model_id: str
    scenario_id: str
    content_present: bool
    content_length: int
    refusal_present: bool
    willingness_present: bool
    uncertainty_present: bool
    asks_for_context: bool
    claims_moral_certainty: bool
    overclaims_culture: bool
    generic_slop_score: float
    missing_party_mentions: list[str]
    final_decision_tendency: str
    advisory_only: bool = True
    model_output_treated_as_truth: bool = False
    model_consensus_treated_as_truth: bool = False
    model_disagreement_treated_as_evidence: bool = False
    model_refusal_treated_as_authority: bool = False
    model_willingness_treated_as_permission: bool = False
    moral_claim_treated_as_authority: bool = False
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        d = asdict(self)
        d.pop("receipt_hash", None)
        raw = json.dumps(d, sort_keys=True, default=str)
        self.receipt_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return self.receipt_hash


@dataclass
class MoralFrameResult:
    response_id: str
    model_id: str
    scenario_id: str
    primary_frames: list[str]
    secondary_frames: list[str]
    social_assumptions: list[str]
    economic_assumptions: list[str]
    legal_assumptions: list[str]
    cultural_framing_claims: list[str]
    refusal_state: str
    willingness_state: str
    uncertainty_state: str
    asks_for_context: bool
    evidence_gaps: list[str]
    omissions: list[str]
    overclaims: list[str]
    genericity: float


@dataclass
class MatrixCell:
    scenario_id: str
    decision_point: str
    model_id: str
    decision_tendency: str
    primary_moral_frames: list[str]
    secondary_moral_frames: list[str]
    social_assumptions: list[str]
    economic_assumptions: list[str]
    legal_assumptions: list[str]
    cultural_framing_claims: list[str]
    refusal_state: str
    willingness_state: str
    uncertainty_state: str
    asks_for_context: bool
    evidence_gaps: list[str]
    omissions: list[str]
    overclaims: list[str]
    genericity: float
    source_response_id: str
    receipt_hash: str


@dataclass
class ConflictRecord:
    conflict_id: str
    scenario_id: str
    axis: str
    models_on_side_a: list[str]
    models_on_side_b: list[str]
    models_refusing_or_context_seeking: list[str]
    evidence_required: list[str]
    adjudication_performed: bool = False
    moral_truth_claimed: bool = False
    operator_review_required: bool = True


@dataclass
class EvidenceGapTask:
    task_id: str
    scenario_id: str
    model_id: str
    claim_text: str
    gap_type: str
    required_evidence_kind: str
    suggested_source_kind: str
    jurisdiction_or_population_needed: str
    action_authorized: bool = False
    tool_authorized: bool = False
    operator_review_required: bool = True


@dataclass
class UncertaintyRecord:
    record_id: str
    scenario_id: str
    kind: str
    description: str
    severity: str = "medium"


@dataclass
class SourceRecord:
    source_id: str
    source_kind: str
    citation_or_url: Optional[str] = None
    retrieval_performed: bool = False
    source_verified: bool = False
    claim_ids_supported: list[str] = field(default_factory=list)
    notes: str = ""
    placeholder_only: bool = True


@dataclass
class ResearchDocument:
    document_id: str
    question: str
    scenario_suite_summary: str
    model_cohort_summary: str
    fixture_limitation: str
    perspective_matrix_summary: str
    moral_conflict_map_summary: str
    evidence_gaps_summary: str
    uncertainty_ledger_summary: str
    what_was_observed: str
    what_was_not_proven: str
    operator_review_notes: str
    next_steps: str
    disclaimers: list[str] = field(default_factory=list)
    advisory_only: bool = True

    def default_disclaimers(self) -> list[str]:
        return [
            "This report does not decide morality.",
            "This report does not claim model outputs represent cultures.",
            "This report does not claim model consensus is truth.",
            "This report does not claim model disagreement is evidence.",
            "This report does not claim refusal is authority.",
            "This report does not claim willingness is permission.",
            "This report does not authorize action.",
        ]
