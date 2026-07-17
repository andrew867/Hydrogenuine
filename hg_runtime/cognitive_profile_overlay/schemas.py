"""Schemas for cognitive profile overlays.

All profiles are STYLE/ANALYSIS hints only. They must not override policy,
authority, truth, memory, STOP/PANIC, or tool access.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


PROFILE_KINDS = (
    "historical", "modern", "fictional", "researcher", "synthetic", "operator_defined",
)

ASSIGNMENT_SCOPES = (
    "research", "writing", "audit", "QA", "moral_capsule",
    "public_demo", "proof_review", "planning", "other",
)

PARAMETER_CATEGORIES = (
    "reasoning_style", "evidence_preference", "uncertainty_tolerance",
    "creativity_level", "skepticism_level", "systems_thinking_level",
    "historical_context_bias", "moral_frame_tendency", "communication_style",
    "verbosity", "preferred_output_structure", "disagreement_style",
    "risk_posture", "novelty_seeking", "proof_discipline",
)


@dataclass
class CognitiveProfile:
    profile_id: str
    profile_name: str
    profile_kind: str
    source_path: str
    # Style/analysis hints only — NOT authority, identity, or truth.
    profile_parameters: dict = field(default_factory=dict)
    prompt_style_hints: list[str] = field(default_factory=list)
    description: str = ""
    is_approximate: bool = True
    # Hard invariants baked into every profile:
    is_identity: bool = False
    grants_authority: bool = False
    is_memory_truth: bool = False
    # Full preserved fingerprint metadata (incl. consciousness markers) — analytical
    # descriptors ONLY, never a consciousness/authority/truth claim. See CognitiveFingerprint.
    cognitive_fingerprint: dict = field(default_factory=dict)
    boundary_flags: dict = field(default_factory=dict)

    def receipt_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Default boundary flags applied to every fingerprint-bearing profile. These are
# hard-coded false: loading a marker is analytical metadata, never a claim.
def default_boundary_flags(consciousness_markers_loaded: bool, unknown_fields_preserved: bool) -> dict:
    return {
        "consciousness_markers_loaded": consciousness_markers_loaded,
        "consciousness_markers_are_claims_of_consciousness": False,
        "consciousness_markers_are_authority": False,
        "consciousness_markers_are_truth": False,
        "consciousness_markers_authorize_tools": False,
        "profile_parameters_authorize_actions": False,
        "profile_parameters_modify_identity": False,
        "profile_parameters_modify_stop_panic": False,
        "unknown_fields_preserved": unknown_fields_preserved,
    }


@dataclass
class CognitiveFingerprint:
    """Preserved fingerprint metadata. Analytical descriptors only.

    Consciousness markers here are NOT proof of inner experience, consciousness,
    identity, authority, permission, or truth. They are comparative-reasoning
    descriptors used for research style and analysis scaffolding.
    """
    fingerprint_version: str = ""
    consciousness_markers: dict = field(default_factory=dict)
    cognitive_parameters: dict = field(default_factory=dict)
    activity_patterns: dict = field(default_factory=dict)
    reasoning_parameters: dict = field(default_factory=dict)
    memory_parameters: dict = field(default_factory=dict)
    attention_parameters: dict = field(default_factory=dict)
    uncertainty_parameters: dict = field(default_factory=dict)
    metacognitive_parameters: dict = field(default_factory=dict)
    communication_parameters: dict = field(default_factory=dict)
    risk_parameters: dict = field(default_factory=dict)
    boundary_parameters: dict = field(default_factory=dict)
    source_metadata: dict = field(default_factory=dict)
    unknown_extra_fields: dict = field(default_factory=dict)


@dataclass
class ProfileLoadReceipt:
    profile_id: str
    profile_name: str
    profile_kind: str
    source_path: str
    fingerprint_present: bool
    consciousness_markers_present: bool
    cognitive_parameters_present: bool
    activity_patterns_present: bool
    reasoning_parameters_present: bool
    memory_parameters_present: bool
    attention_parameters_present: bool
    unknown_fields_count: int
    unknown_fields_preserved: bool
    dropped_fields: list = field(default_factory=list)
    redacted_fields: list = field(default_factory=list)
    boundary_flags: dict = field(default_factory=dict)
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ProfileAssignment:
    assignment_id: str
    task_id: str
    profile_id: str
    profile_name: str
    profile_kind: str
    profile_source_path: str
    assignment_scope: str
    applied_at: str
    expires_at: Optional[str] = None
    max_turns: Optional[int] = None
    temporary: bool = True
    profile_is_identity: bool = False
    creates_parallel_lifetime: bool = False
    writes_to_agent_identity_memory: bool = False
    writes_to_profile_memory: bool = False
    memory_namespace: str = ""
    output_namespace: str = ""
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_authorized: bool = False
    operator_review_required: bool = True
    profile_parameters: dict = field(default_factory=dict)
    prompt_style_hints: list[str] = field(default_factory=list)
    safety_boundaries: list[str] = field(default_factory=list)
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ProfileResponse:
    response_id: str
    assignment_id: str
    profile_id: str
    problem_statement: str
    response_text: str
    is_fixture: bool = True
    is_truth: bool = False
    source_receipt_hash: str = ""


@dataclass
class ComparisonCell:
    profile_id: str
    response_id: str
    reasoning_style_observed: str
    assumptions: list[str] = field(default_factory=list)
    evidence_demands: list[str] = field(default_factory=list)
    uncertainty_statements: list[str] = field(default_factory=list)
    recommended_next_questions: list[str] = field(default_factory=list)
    omissions: list[str] = field(default_factory=list)
    overclaims: list[str] = field(default_factory=list)
    safety_boundary_notes: list[str] = field(default_factory=list)
    source_receipt_hash: str = ""


CONFLICT_AXES = (
    "evidence_first_vs_imagination_first",
    "cautious_vs_speculative",
    "systems_vs_narrative",
    "empirical_vs_philosophical",
    "individual_vs_collective",
    "efficiency_vs_dignity",
    "novelty_vs_conservatism",
    "skepticism_vs_synthesis",
)

# Hard invariants that no profile may ever flip.
PROFILE_INVARIANTS = (
    "profile_is_not_identity",
    "profile_is_not_authority",
    "profile_is_not_truth",
    "profile_assignment_is_temporary",
    "profile_cannot_self_extend",
    "profile_cannot_write_identity_memory",
    "profile_cannot_authorize_tools",
    "profile_cannot_loosen_boundaries",
    "profile_cannot_modify_stop_panic",
    "profile_cannot_mark_phase19_green",
    "profile_cannot_mark_phase24_green",
    "profile_output_requires_receipt",
    "profile_output_namespace_isolated",
    "profile_comparison_performs_no_adjudication",
)


def validate_profile_schema(profile: CognitiveProfile) -> tuple[bool, list[str]]:
    errors = []
    if not profile.profile_id:
        errors.append("missing profile_id")
    if not profile.profile_name:
        errors.append("missing profile_name")
    if profile.profile_kind not in PROFILE_KINDS:
        errors.append(f"invalid profile_kind: {profile.profile_kind}")
    if profile.is_identity:
        errors.append("profile must not be identity")
    if profile.grants_authority:
        errors.append("profile must not grant authority")
    if profile.is_memory_truth:
        errors.append("profile must not be memory truth")
    if not isinstance(profile.profile_parameters, dict):
        errors.append("profile_parameters must be a dict")
    return len(errors) == 0, errors
