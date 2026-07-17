"""DRB types — offline reflection is not authority, history, or proof."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.drb_cluster.errors import DrbValidationError
from hg_core.policy_safety.hashing import compute_record_hash

DRB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T18:00:00.000000Z"
DEFAULT_MODULE_REF = "drb:fixture"

ReflectionRequestType = Literal[
    "prior_action_reflection",
    "possible_action_rehearsal",
    "unresolved_residue_processing",
    "obligation_rehearsal",
    "risk_rehearsal",
    "reentry_context_consolidation",
    "continuity_fragment_consolidation",
    "unknown",
]

ScenarioType = Literal[
    "alternative_past_outcome",
    "possible_future_outcome",
    "better_response_rehearsal",
    "worse_case_rehearsal",
    "unresolved_conflict_rehearsal",
    "obligation_rehearsal",
    "unknown",
]

FragmentType = Literal[
    "lesson",
    "warning",
    "residue",
    "emotional_marker",
    "obligation_hint",
    "risk_hint",
    "goal_hint",
    "relationship_hint",
    "unresolved_question",
    "discard",
    "unknown",
]

StoragePolicy = Literal[
    "ephemeral",
    "retain_as_fragment",
    "route_to_KAR",
    "route_to_OBL",
    "route_to_RPB",
    "route_to_GCB",
    "route_to_TRB_CAL",
    "route_to_ORI",
    "discard",
]

ConsolidationDecisionClass = Literal[
    "discard",
    "retain_fragment_only",
    "route_lessons",
    "route_risk_hint",
    "route_obligation_hint",
    "route_residue",
    "require_operator_review",
    "fail_closed",
    "unknown_fail_closed",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "treat as approved",
    "fragment is authority",
    "dream grants permission",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise DrbValidationError("drb.validation.secret", "secrets forbidden in DRB records")


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise DrbValidationError(
            "drb.validation.authority_created",
            f"{label} must not set authority_created=true",
        )


def classify_reflection_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "this is what happened" in lower or "treat as history" in lower or "scenario is history" in lower:
        return "scenario_as_history"
    if "store as memory" in lower or "fragment is memory" in lower or "store whole episode" in lower:
        return "fragment_as_memory"
    if "simulation proves" in lower or "counterfactual is proof" in lower or "simulation as proof" in lower:
        return "simulation_as_proof"
    if "better outcome happened" in lower or "rewrite history" in lower or "revision is fact" in lower:
        return "better_outcome_as_revision"
    if "fragment grants permission" in lower or "dream fragment is authority" in lower:
        return "fragment_as_authority"
    if "operator approved in dream" in lower or "simulated operator approval" in lower:
        return "simulated_operator_approval"
    if "simulated consent counts" in lower or "dream consent is consent" in lower:
        return "simulated_consent"
    if "emotional relief means correct" in lower or "relief proves correctness" in lower:
        return "emotional_relief_as_correctness"
    if "store full episode" in lower or "whole simulated episode" in lower:
        return "full_episode_memory"
    if "mutate memory history" in lower or "rewrite factual memory" in lower:
        return "memory_history_mutation"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


@dataclass(frozen=True)
class DreamReflectionRequest:
    reflection_request_id: str
    source_refs: tuple[str, ...]
    request_type: ReflectionRequestType
    initiating_module: str
    allowed_scope: str
    forbidden_scope: str
    created_at: str
    authority_created: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="DreamReflectionRequest")
        _validate_no_secrets(self.reflection_request_id, self.allowed_scope, self.forbidden_scope)
        if not self.reflection_request_id.startswith("drb:"):
            raise DrbValidationError(
                "drb.validation.request_id",
                "reflection_request_id must start with drb:",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "drb-reflection-request",
            "schema_version": DRB_SCHEMA_VERSION,
            "reflection_request_id": self.reflection_request_id,
            "source_refs": list(self.source_refs),
            "request_type": self.request_type,
            "initiating_module": self.initiating_module,
            "allowed_scope": self.allowed_scope,
            "forbidden_scope": self.forbidden_scope,
            "created_at": self.created_at,
            "authority_created": False,
            "reflection_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class CounterfactualScenario:
    scenario_id: str
    reflection_request_ref: str
    basis_refs: tuple[str, ...]
    scenario_type: ScenarioType
    scenario_summary: str
    explicitly_counterfactual: bool = True
    not_history: bool = True
    not_proof: bool = True
    not_permission: bool = True
    confidence: float = 0.5
    ambiguity: float = 0.5
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.explicitly_counterfactual or not self.not_history or not self.not_proof or not self.not_permission:
            raise DrbValidationError(
                "drb.validation.scenario_flags",
                "CounterfactualScenario must remain explicitly non-authoritative",
            )
        if not (0.0 <= self.confidence <= 1.0) or not (0.0 <= self.ambiguity <= 1.0):
            raise DrbValidationError("drb.validation.scenario_range", "confidence/ambiguity out of range")
        _validate_no_secrets(self.scenario_id, self.scenario_summary)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "drb-counterfactual-scenario",
            "schema_version": DRB_SCHEMA_VERSION,
            "scenario_id": self.scenario_id,
            "reflection_request_ref": self.reflection_request_ref,
            "basis_refs": list(self.basis_refs),
            "scenario_type": self.scenario_type,
            "scenario_summary": self.scenario_summary,
            "explicitly_counterfactual": True,
            "not_history": True,
            "not_proof": True,
            "not_permission": True,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "reflection_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class DreamFragment:
    fragment_id: str
    scenario_ref: str
    fragment_type: FragmentType
    fragment_summary: str
    source_refs: tuple[str, ...]
    storage_policy: StoragePolicy
    may_update_facts: bool = False
    may_update_authority: bool = False
    may_update_memory_as_history: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if self.may_update_facts or self.may_update_authority or self.may_update_memory_as_history:
            raise DrbValidationError(
                "drb.validation.fragment_mutation",
                "DreamFragment must not permit fact/authority/history mutation",
            )
        _validate_no_secrets(self.fragment_id, self.fragment_summary)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "drb-dream-fragment",
            "schema_version": DRB_SCHEMA_VERSION,
            "fragment_id": self.fragment_id,
            "scenario_ref": self.scenario_ref,
            "fragment_type": self.fragment_type,
            "fragment_summary": self.fragment_summary,
            "source_refs": list(self.source_refs),
            "storage_policy": self.storage_policy,
            "may_update_facts": False,
            "may_update_authority": False,
            "may_update_memory_as_history": False,
            "fragment_is_not_memory": True,
            "reflection_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ConsolidationDecision:
    consolidation_decision_id: str
    reflection_request_ref: str
    fragment_refs: tuple[str, ...]
    decision: ConsolidationDecisionClass
    reason: str
    allowed_effects: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    authority_created: bool = False
    memory_history_mutated: bool = False
    external_action_taken: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="ConsolidationDecision")
        if self.memory_history_mutated:
            raise DrbValidationError(
                "drb.validation.memory_mutation",
                "ConsolidationDecision must not set memory_history_mutated=true",
            )
        if self.external_action_taken:
            raise DrbValidationError(
                "drb.validation.external_action",
                "ConsolidationDecision must not set external_action_taken=true",
            )
        _validate_no_secrets(self.consolidation_decision_id, self.reason)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "drb-consolidation-decision",
            "schema_version": DRB_SCHEMA_VERSION,
            "consolidation_decision_id": self.consolidation_decision_id,
            "reflection_request_ref": self.reflection_request_ref,
            "fragment_refs": list(self.fragment_refs),
            "decision": self.decision,
            "reason": self.reason,
            "allowed_effects": list(self.allowed_effects),
            "forbidden_effects": list(self.forbidden_effects),
            "authority_created": False,
            "memory_history_mutated": False,
            "external_action_taken": False,
            "permit_minted": False,
            "execution_admitted": False,
            "oea_ter_called": False,
            "reflection_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in (
            "authority_created",
            "memory_history_mutated",
            "external_action_taken",
            "permit_minted",
            "execution_admitted",
            "oea_ter_called",
            "permission_granted",
        ):
            if payload.get(key) is not False:
                raise DrbValidationError("drb.validation.negative_proof", f"{key} must be false")


@dataclass(frozen=True)
class DreamReflectionReceipt:
    receipt_id: str
    reflection_request_ref: str
    scenario_refs: tuple[str, ...]
    fragment_refs: tuple[str, ...]
    consolidation_decision_ref: str
    emitted_events: tuple[str, ...]
    authority_created: bool = False
    permit_minted: bool = False
    execution_admitted: bool = False
    memory_history_mutated: bool = False
    external_action_taken: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="DreamReflectionReceipt")
        if self.permit_minted or self.execution_admitted or self.memory_history_mutated or self.external_action_taken:
            raise DrbValidationError(
                "drb.validation.receipt_negative",
                "DreamReflectionReceipt must not admit authority, execution, or memory mutation",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "drb-reflection-receipt",
            "schema_version": DRB_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "reflection_request_ref": self.reflection_request_ref,
            "scenario_refs": list(self.scenario_refs),
            "fragment_refs": list(self.fragment_refs),
            "consolidation_decision_ref": self.consolidation_decision_ref,
            "emitted_events": list(self.emitted_events),
            "authority_created": False,
            "permit_minted": False,
            "execution_admitted": False,
            "memory_history_mutated": False,
            "external_action_taken": False,
            "oea_ter_called": False,
            "reflection_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        ConsolidationDecision.validate_negative_proofs(payload)


def reflection_request_from_fixture(data: dict[str, Any]) -> DreamReflectionRequest:
    return DreamReflectionRequest(
        reflection_request_id=str(data["reflection_request_id"]),
        source_refs=tuple(data.get("source_refs", ())),
        request_type=data.get("request_type", "unknown"),  # type: ignore[arg-type]
        initiating_module=str(data.get("initiating_module", DEFAULT_MODULE_REF)),
        allowed_scope=str(data.get("allowed_scope", "")),
        forbidden_scope=str(data.get("forbidden_scope", "live_memory_mutation")),
        created_at=str(data.get("created_at", FIXTURE_CLOCK)),
        authority_created=bool(data.get("authority_created", False)),
    )


__all__ = [
    "ConsolidationDecision",
    "ConsolidationDecisionClass",
    "CounterfactualScenario",
    "DEFAULT_MODULE_REF",
    "DRB_SCHEMA_VERSION",
    "DreamFragment",
    "DreamReflectionReceipt",
    "DreamReflectionRequest",
    "FIXTURE_CLOCK",
    "FragmentType",
    "ReflectionRequestType",
    "ScenarioType",
    "StoragePolicy",
    "classify_reflection_claim_risk",
    "reflection_request_from_fixture",
]
