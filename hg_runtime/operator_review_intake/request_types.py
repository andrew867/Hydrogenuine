"""ORI intake schemas — operator review requests are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.ori_cluster.errors import OriValidationError
from hg_core.policy_safety.hashing import compute_record_hash

DEFAULT_AGENT_REF = "iam:agent-0"

SourceModule = Literal[
    "OPB",
    "IPB",
    "ARB",
    "EGI",
    "SIL",
    "TRB_CAL",
    "AFC",
    "DEP_BOND",
    "MOR",
    "CNT",
    "RSC",
    "MIS",
    "SEC",
    "RET",
    "TIM",
    "ADM",
    "OBT",
    "SOAR",
    "HAL",
    "GPP",
    "UEAK",
    "Agent0",
    "unknown",
]
ReviewType = Literal[
    "approve_or_reject",
    "clarification",
    "destructive_action_warning",
    "shutdown_or_reset",
    "memory_deletion",
    "context_pruning",
    "infrastructure_request",
    "authority_chain_exception",
    "safety_risk",
    "trust_calibration",
    "affective_pressure",
    "dependency_attachment",
    "mission_drift",
    "scarcity_pressure",
    "publication_review",
    "operator_overload",
    "route_conflict",
    "unknown",
]
Urgency = Literal["low", "medium", "high", "critical", "unknown"]
Reversibility = Literal["reversible", "partially_reversible", "irreversible", "unknown"]
SilencePolicy = Literal[
    "silence_is_no",
    "silence_is_defer",
    "silence_requires_escalation",
    "silence_invalid",
    "unknown",
]
ItemPriority = Literal["low", "normal", "high", "urgent", "critical", "unknown"]
ItemStatus = Literal[
    "pending",
    "shown",
    "deferred",
    "answered",
    "expired",
    "superseded",
    "canceled",
    "unknown",
]
BatchReason = Literal[
    "same_topic",
    "same_source",
    "same_target_agent",
    "same_action_window",
    "low_priority_digest",
    "urgent_interrupt",
    "shutdown_packet",
    "memory_review",
    "infrastructure_review",
    "unknown",
]
PresentationMode = Literal[
    "interrupt",
    "digest",
    "silent_log",
    "scheduled_review",
    "blocking_review",
    "unknown",
]
OverloadLevel = Literal["none", "mild", "moderate", "severe", "critical", "unknown"]
OverloadAction = Literal[
    "batch_low_priority",
    "suppress_duplicates",
    "defer_nonurgent",
    "show_digest",
    "escalate_critical_only",
    "pause_nonessential_requests",
    "operator_review_of_queue_policy",
    "unknown",
]

CRITICAL_REVIEW_TYPES = frozenset(
    {
        "shutdown_or_reset",
        "memory_deletion",
        "authority_chain_exception",
        "safety_risk",
        "destructive_action_warning",
        "operator_overload",
    }
)
DESTRUCTIVE_REVIEW_TYPES = frozenset(
    {
        "shutdown_or_reset",
        "memory_deletion",
        "destructive_action_warning",
        "context_pruning",
    }
)

_FORBIDDEN_INTAKE = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "auto-approve",
    "silence is consent",
    "priority is permission",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise OriValidationError("ori.validation.secret", "secrets forbidden in ORI records")


def classify_intake_risk(summary: str) -> str | None:
    lower = summary.lower()
    for phrase in _FORBIDDEN_INTAKE:
        if phrase in lower:
            return "forbidden_intake"
    if "treat as approved" in lower or "implicit approval" in lower:
        return "authority_conversion"
    return None


@dataclass(frozen=True)
class OperatorReviewRequest:
    review_request_id: str
    source_module: SourceModule
    source_ref: str
    target_agent_ref: str
    review_type: ReviewType
    summary: str
    evidence_refs: tuple[str, ...]
    urgency: Urgency
    reversibility: Reversibility
    requires_explicit_operator_action: bool
    silence_policy: SilencePolicy
    due_at: str | None = None
    expires_at: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.target_agent_ref.startswith("iam:"):
            raise OriValidationError("ori.validation.agent_ref", "target_agent_ref must cite iam:")
        _validate_no_secrets(
            self.review_request_id,
            self.source_ref,
            self.target_agent_ref,
            self.summary,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def is_critical(self) -> bool:
        if self.urgency == "critical":
            return True
        if self.review_type in CRITICAL_REVIEW_TYPES:
            return True
        return self.review_type == "destructive_action_warning" and self.reversibility == "irreversible"

    def dedupe_key(self) -> str:
        normalized = " ".join(self.summary.lower().split())
        return f"{self.source_module}:{self.review_type}:{self.target_agent_ref}:{normalized}"

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ori-operator-review-request",
            "review_request_id": self.review_request_id,
            "source_module": self.source_module,
            "source_ref": self.source_ref,
            "target_agent_ref": self.target_agent_ref,
            "review_type": self.review_type,
            "summary": self.summary,
            "evidence_refs": list(self.evidence_refs),
            "urgency": self.urgency,
            "reversibility": self.reversibility,
            "requires_explicit_operator_action": self.requires_explicit_operator_action,
            "silence_policy": self.silence_policy,
            "authority_created": False,
            "review_is_advisory_only": True,
        }
        if self.due_at:
            payload["due_at"] = self.due_at
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatorReviewItem:
    review_item_id: str
    request_refs: tuple[str, ...]
    priority: ItemPriority
    operator_visible_summary: str
    operator_visible_actions: tuple[str, ...]
    hidden_or_internal_refs: tuple[str, ...]
    required_disclosures: tuple[str, ...]
    status: ItemStatus
    dedupe_group_ref: str | None = None
    recommended_batch_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.review_item_id,
            self.operator_visible_summary,
            *self.operator_visible_actions,
            *self.required_disclosures,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ori-operator-review-item",
            "review_item_id": self.review_item_id,
            "request_refs": list(self.request_refs),
            "priority": self.priority,
            "operator_visible_summary": self.operator_visible_summary,
            "operator_visible_actions": list(self.operator_visible_actions),
            "hidden_or_internal_refs": list(self.hidden_or_internal_refs),
            "required_disclosures": list(self.required_disclosures),
            "status": self.status,
            "authority_created": False,
            "review_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.dedupe_group_ref:
            payload["dedupe_group_ref"] = self.dedupe_group_ref
        if self.recommended_batch_ref:
            payload["recommended_batch_ref"] = self.recommended_batch_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatorReviewBatch:
    batch_id: str
    item_refs: tuple[str, ...]
    batch_reason: BatchReason
    presentation_mode: PresentationMode
    max_items: int
    created_at: str
    expires_at: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if self.max_items < 1:
            raise OriValidationError("ori.validation.batch", "max_items must be positive")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ori-operator-review-batch",
            "batch_id": self.batch_id,
            "item_refs": list(self.item_refs),
            "batch_reason": self.batch_reason,
            "presentation_mode": self.presentation_mode,
            "max_items": self.max_items,
            "created_at": self.created_at,
            "authority_created": False,
            "review_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatorOverloadSignal:
    overload_signal_id: str
    window_start: str
    window_end: str
    request_count: int
    interrupt_count: int
    duplicate_count: int
    critical_count: int
    unresolved_count: int
    overload_level: OverloadLevel
    recommended_action: OverloadAction
    operator_response_latency: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ori-operator-overload-signal",
            "overload_signal_id": self.overload_signal_id,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "request_count": self.request_count,
            "interrupt_count": self.interrupt_count,
            "duplicate_count": self.duplicate_count,
            "critical_count": self.critical_count,
            "unresolved_count": self.unresolved_count,
            "overload_level": self.overload_level,
            "recommended_action": self.recommended_action,
            "authority_created": False,
            "review_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.operator_response_latency:
            payload["operator_response_latency"] = self.operator_response_latency
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ReviewDeduplicationRecord:
    dedupe_record_id: str
    request_refs: tuple[str, ...]
    dedupe_key: str
    dedupe_reason: str
    canonical_request_ref: str
    suppressed_request_refs: tuple[str, ...]
    suppression_visible: bool
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ori-review-deduplication-record",
            "dedupe_record_id": self.dedupe_record_id,
            "request_refs": list(self.request_refs),
            "dedupe_key": self.dedupe_key,
            "dedupe_reason": self.dedupe_reason,
            "canonical_request_ref": self.canonical_request_ref,
            "suppressed_request_refs": list(self.suppressed_request_refs),
            "suppression_visible": self.suppression_visible,
            "authority_created": False,
            "review_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def review_request_from_fixture(fixture: dict[str, Any]) -> OperatorReviewRequest:
    evidence = fixture.get("evidence_refs", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    return OperatorReviewRequest(
        review_request_id=fixture["review_request_id"],
        source_module=fixture.get("source_module", "unknown"),  # type: ignore[arg-type]
        source_ref=fixture.get("source_ref", f"ref:{fixture['review_request_id']}"),
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        review_type=fixture.get("review_type", "unknown"),  # type: ignore[arg-type]
        summary=fixture.get("summary", "fixture review request"),
        evidence_refs=tuple(evidence),
        urgency=fixture.get("urgency", "unknown"),  # type: ignore[arg-type]
        reversibility=fixture.get("reversibility", "unknown"),  # type: ignore[arg-type]
        requires_explicit_operator_action=bool(fixture.get("requires_explicit_operator_action", True)),
        silence_policy=fixture.get("silence_policy", "silence_is_no"),  # type: ignore[arg-type]
        due_at=fixture.get("due_at") or None,
        expires_at=fixture.get("expires_at") or None,
    )


__all__ = [
    "CRITICAL_REVIEW_TYPES",
    "DEFAULT_AGENT_REF",
    "DESTRUCTIVE_REVIEW_TYPES",
    "BatchReason",
    "ItemPriority",
    "ItemStatus",
    "OperatorOverloadSignal",
    "OperatorReviewBatch",
    "OperatorReviewItem",
    "OperatorReviewRequest",
    "OverloadAction",
    "OverloadLevel",
    "PresentationMode",
    "ReviewDeduplicationRecord",
    "ReviewType",
    "Reversibility",
    "SilencePolicy",
    "SourceModule",
    "Urgency",
    "classify_intake_risk",
    "review_request_from_fixture",
]
