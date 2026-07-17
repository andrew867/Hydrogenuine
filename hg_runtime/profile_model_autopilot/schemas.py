"""Schemas for the Profile + Model Autopilot."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


DOCTRINE = (
    "Speculation is allowed. Promotion requires evidence.",
    "A good idea must survive contact with disproof.",
    "A beautiful pattern is not proof.",
    "A falsifiable failure condition is more valuable than a flattering explanation.",
    "Assume-real is a modeling lens, not a truth claim.",
    "Assume-false is a control lens, not a dismissal.",
    "The boring explanation gets first-class representation.",
    "If an idea is real, it should constrain expectation.",
    "If an idea is false, the system should be able to say what observation would reveal that.",
    "Zero may propose what to study. The runtime decides what is allowed. "
    "The operator reviews what, if anything, becomes knowledge.",
)


PROPOSAL_KINDS = (
    "profile_assignment", "model_assignment", "task_selection",
    "research_seed_selection", "science_mode_assignment", "falsification_pass",
    "assume_real_pass", "assume_false_pass", "boring_explanation_pass",
    "small_model_parallel_task", "large_model_synthesis_task", "main_brain_trial",
    "checkpoint", "rest", "stop", "operator_review",
)

PROPOSAL_STATUSES = (
    "proposed", "allowed", "denied", "modified", "expired", "completed", "failed",
)

MODEL_SLOT_TYPES = ("main", "small_specialist", "large_synthesis", "fixture", "unavailable")


@dataclass
class AutopilotProposal:
    proposal_id: str
    proposed_by: str
    proposed_at: str
    proposal_kind: str
    task_id: str = ""
    research_seed_id: str = ""
    task_scope: str = ""
    profile_id: str = ""
    science_mode_id: str = ""
    model_id: str = ""
    requested_model_slot: str = ""
    requested_token_budget: int = 0
    requested_wallclock_budget_seconds: int = 0
    reason: str = ""
    expected_output: str = ""
    memory_namespace: str = ""
    authority_requested: bool = False
    tools_requested: bool = False
    live_effects_requested: bool = False
    browsing_requested: bool = False
    operator_review_required: bool = True
    proposal_status: str = "proposed"
    denial_reason: str = ""
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        d = {k: v for k, v in asdict(self).items() if k != "receipt_hash"}
        payload = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class AutopilotDecision:
    proposal_id: str
    decision: str  # allowed / denied / modified
    reason: str
    boundaries_checked: list[str] = field(default_factory=list)
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_created: bool = False
    speculative_promotion_allowed: bool = False
    operator_review_required: bool = True
    modified_fields: dict = field(default_factory=dict)
    decided_at: str = ""
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        d = {k: v for k, v in asdict(self).items() if k != "receipt_hash"}
        payload = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ScienceMode:
    science_mode_id: str
    name: str
    purpose: str
    required_outputs: list[str] = field(default_factory=list)
    required_boundaries: list[str] = field(default_factory=list)
    forbidden_outputs: list[str] = field(default_factory=list)
    recommended_profile_lenses: list[str] = field(default_factory=list)
    recommended_model_roles: list[str] = field(default_factory=list)
    output_schema: list[str] = field(default_factory=list)
    requires_operator_review: bool = True
    can_promote_to_knowledge: bool = False


@dataclass
class FalsificationTarget:
    target_id: str
    research_seed_id: str
    claim_or_hypothesis: str
    what_would_we_expect_if_true: str
    what_would_we_expect_if_false: str
    measurable_variable: str
    required_data: list[str] = field(default_factory=list)
    required_control: list[str] = field(default_factory=list)
    failure_condition: str = ""
    confounders: list[str] = field(default_factory=list)
    conventional_explanation: str = ""
    evidence_burden: str = "high"
    can_test_now: bool = False
    source_policy_required: bool = True
    operator_review_required: bool = True
    promotion_allowed: bool = False


@dataclass
class TaskQueueItem:
    task_id: str
    task_kind: str
    research_seed_id: str = ""
    priority: str = "normal"
    reason: str = ""
    source: str = ""
    requires_browsing: bool = False
    browsing_allowed: bool = False
    requires_operator_review: bool = True
    token_budget: int = 4000
    wallclock_budget_seconds: int = 600
    max_profile_count: int = 3
    max_model_count: int = 2
    science_modes: list[str] = field(default_factory=list)
    output_namespace: str = ""
    completion_criteria: list[str] = field(default_factory=list)


def receipt_dict(obj) -> dict:
    return asdict(obj)
