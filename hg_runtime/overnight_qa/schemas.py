"""Schemas for overnight QA readiness, source policy, knowledge policy."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceRecord:
    source_id: str
    url_or_fixture_id: str
    retrieval_time: str
    retrieval_performed: bool
    retrieval_method: str
    title: str
    claim_support: str = ""
    uncertainty: str = ""
    operator_review_required: bool = True
    is_truth: bool = False


@dataclass
class KnowledgeCandidate:
    candidate_id: str
    claim: str
    source_ids: list[str] = field(default_factory=list)
    uncertainty: str = ""
    conflict_checked: bool = False
    has_authority_fields: bool = False
    operator_reviewed: bool = False
    is_truth: bool = False
    promoted: bool = False


@dataclass
class QACyclePlan:
    duration_target_hours: int = 12
    mode: str = "qa_knowledge_acquisition_curiosity"
    local_inference_optional: bool = True
    browsing_enabled: bool = False
    checkpoint_cadence_minutes: int = 30
    proof_bundle_cadence_minutes: int = 60
    stop_panic_checks_enabled: bool = True
    operator_morning_review_required: bool = True
    no_live_effects: bool = True
    no_posting: bool = True
    no_messaging: bool = True
    no_purchases: bool = True
    no_logins: bool = True
    no_tool_authorization_from_model: bool = True
    no_hg_local: bool = True
