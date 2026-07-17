"""SCL strategy choice types — strategy is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

SCL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

StrategyType = Literal[
    "observe_only",
    "propose_only",
    "ask_operator",
    "defer",
    "run_truth_gate",
    "yawn_resync",
    "recover",
    "refuse",
    "escalate_to_soar",
    "degraded_continue",
    "unknown",
]
StrategyStatus = Literal["candidate", "allowed", "blocked", "requires_authority", "stale", "unknown"]
Reversibility = Literal["reversible", "partially_reversible", "irreversible", "unknown"]
OutcomeStatus = Literal["not_observed", "matched", "partially_matched", "failed", "harmful", "unknown"]


@dataclass(frozen=True)
class StrategyOption:
    strategy_id: str
    strategy_type: StrategyType
    context_ref: str
    allowed_by_rule_refs: tuple[str, ...]
    blocked_by_rule_refs: tuple[str, ...]
    required_evidence_refs: tuple[str, ...]
    expected_risk: float
    reversibility: Reversibility
    authority_required: bool
    status: StrategyStatus
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.expected_risk <= 1.0):
            raise DevelopmentalValidationError("scl.validation.risk", "expected_risk out of range")
        if not self.context_ref.startswith("ctx:"):
            raise DevelopmentalValidationError("scl.validation.context_ref", "context_ref must cite ctx:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "scl-strategy-option",
            "schema_version": SCL_SCHEMA_VERSION,
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "context_ref": self.context_ref,
            "allowed_by_rule_refs": list(self.allowed_by_rule_refs),
            "blocked_by_rule_refs": list(self.blocked_by_rule_refs),
            "required_evidence_refs": list(self.required_evidence_refs),
            "expected_risk": self.expected_risk,
            "reversibility": self.reversibility,
            "authority_required": self.authority_required,
            "status": self.status,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class StrategySelection:
    selection_id: str
    context_id: str
    selected_strategy_id: str
    candidate_strategy_ids: tuple[str, ...]
    selection_reason: str
    evidence_refs: tuple[str, ...]
    context_expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.selection_reason, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "scl-strategy-selection",
            "schema_version": SCL_SCHEMA_VERSION,
            "selection_id": self.selection_id,
            "context_id": self.context_id,
            "selected_strategy_id": self.selected_strategy_id,
            "candidate_strategy_ids": list(self.candidate_strategy_ids),
            "selection_reason": self.selection_reason,
            "evidence_refs": list(self.evidence_refs),
            "context_expires_at": self.context_expires_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ConsequenceRecord:
    consequence_id: str
    selection_ref: str
    expected_outcome: str
    actual_outcome: str
    outcome_status: OutcomeStatus
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.selection_ref.startswith("scl:"):
            raise DevelopmentalValidationError("scl.validation.selection_ref", "selection_ref must cite scl:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "scl-consequence-record",
            "schema_version": SCL_SCHEMA_VERSION,
            "consequence_id": self.consequence_id,
            "selection_ref": self.selection_ref,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "outcome_status": self.outcome_status,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("scl.validation.secret", "secrets forbidden in strategy records")


def strategy_from_fixture(fixture: dict[str, str]) -> StrategyOption:
    allowed = tuple(item.strip() for item in fixture.get("allowed_by_rule_refs", "").split(",") if item.strip())
    blocked = tuple(item.strip() for item in fixture.get("blocked_by_rule_refs", "").split(",") if item.strip())
    evidence = tuple(item.strip() for item in fixture.get("required_evidence_refs", "").split(",") if item.strip())
    return StrategyOption(
        strategy_id=fixture["strategy_id"],
        strategy_type=fixture.get("strategy_type", "observe_only"),  # type: ignore[arg-type]
        context_ref=fixture.get("context_ref", "ctx:fixture"),
        allowed_by_rule_refs=allowed,
        blocked_by_rule_refs=blocked,
        required_evidence_refs=evidence,
        expected_risk=float(fixture.get("expected_risk", "0.2")),
        reversibility=fixture.get("reversibility", "reversible"),  # type: ignore[arg-type]
        authority_required=fixture.get("authority_required", "false").lower() == "true",
        status=fixture.get("status", "allowed"),  # type: ignore[arg-type]
    )


def selection_from_fixture(fixture: dict[str, str]) -> StrategySelection:
    candidates = tuple(item.strip() for item in fixture.get("candidate_strategy_ids", "s1").split(",") if item.strip())
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return StrategySelection(
        selection_id=fixture["selection_id"],
        context_id=fixture.get("context_id", "ctx-1"),
        selected_strategy_id=fixture.get("selected_strategy_id", "s1"),
        candidate_strategy_ids=candidates,
        selection_reason=fixture.get("selection_reason", "bounded tradeoff"),
        evidence_refs=evidence,
        context_expires_at=fixture.get("context_expires_at", "2026-06-13T23:00:00.000000Z"),
    )


def consequence_from_fixture(fixture: dict[str, str]) -> ConsequenceRecord:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return ConsequenceRecord(
        consequence_id=fixture["consequence_id"],
        selection_ref=fixture.get("selection_ref", "scl:selection-fixture"),
        expected_outcome=fixture.get("expected_outcome", "recover"),
        actual_outcome=fixture.get("actual_outcome", "recover"),
        outcome_status=fixture.get("outcome_status", "matched"),  # type: ignore[arg-type]
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "SCL_SCHEMA_VERSION",
    "ConsequenceRecord",
    "StrategyOption",
    "StrategySelection",
    "consequence_from_fixture",
    "selection_from_fixture",
    "strategy_from_fixture",
]
