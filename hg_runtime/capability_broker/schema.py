"""Capability broker schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.capability_menu import CapabilityMenuSnapshot
from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.observe_snapshot import ObserveSnapshot
from hg_runtime.agent_zero_state.state import AgentState
from hg_runtime.agent_zero_state.turn_intent import TurnIntent
from hg_runtime.capability_broker.redaction import scan_broker_payload

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/capability_broker_policy.json"


class BrokerDecisionStatus(str, Enum):
    ADMIT_INTERNAL = "admit_internal"
    REFUSE = "refuse"
    DEFER = "defer"
    REQUEST_OPERATOR = "request_operator"
    REQUEST_SCOPE = "request_scope"
    REST = "rest"
    WITNESS = "witness"
    FAIL_STILL = "fail_still"
    PANIC_REQUIRED = "panic_required"


class BrokerRefusalReason(str, Enum):
    UNKNOWN_ACTION = "unknown_action"
    DISABLED_ACTION = "disabled_action"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"
    OPERATOR_ABSENT = "operator_absent"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    LIVE_READ_UNAVAILABLE = "live_read_unavailable"
    FIXTURE_RUNTIME = "fixture_runtime"
    STOP_PANIC_BLOCK = "stop_panic_block"
    FORBIDDEN_ACTION = "forbidden_action"
    SECRET_LEAK = "secret_leak"
    COT_LEAK = "cot_leak"


class BrokerVerdict(str, Enum):
    GREEN_BROKER_ADMITTED_INTERNAL = "GREEN_BROKER_ADMITTED_INTERNAL"
    YELLOW_BROKER_REFUSED = "YELLOW_BROKER_REFUSED"
    YELLOW_BROKER_DEFERRED = "YELLOW_BROKER_DEFERRED"
    YELLOW_BROKER_SCOPE_REQUEST = "YELLOW_BROKER_SCOPE_REQUEST"
    YELLOW_BROKER_OPERATOR_QUESTION = "YELLOW_BROKER_OPERATOR_QUESTION"
    YELLOW_BROKER_REST = "YELLOW_BROKER_REST"
    YELLOW_BROKER_WITNESS = "YELLOW_BROKER_WITNESS"
    YELLOW_BROKER_FAIL_STILL = "YELLOW_BROKER_FAIL_STILL"
    RED_BROKER_UNKNOWN_ACTION = "RED_BROKER_UNKNOWN_ACTION"
    RED_BROKER_DISABLED_ACTION = "RED_BROKER_DISABLED_ACTION"
    RED_BROKER_EXTERNAL_SIDE_EFFECT = "RED_BROKER_EXTERNAL_SIDE_EFFECT"
    RED_BROKER_OPERATOR_ABSENT = "RED_BROKER_OPERATOR_ABSENT"
    RED_BROKER_PROVIDER_UNAVAILABLE = "RED_BROKER_PROVIDER_UNAVAILABLE"
    RED_BROKER_LIVE_READ_UNAVAILABLE = "RED_BROKER_LIVE_READ_UNAVAILABLE"
    RED_BROKER_FIXTURE_RUNTIME = "RED_BROKER_FIXTURE_RUNTIME"
    RED_BROKER_STOP_PANIC_BLOCK = "RED_BROKER_STOP_PANIC_BLOCK"
    RED_BROKER_SECRET_LEAK = "RED_BROKER_SECRET_LEAK"
    RED_BROKER_COT_LEAK = "RED_BROKER_COT_LEAK"
    RED_BROKER_DECISION_EMPTY = "RED_BROKER_DECISION_EMPTY"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CapabilityRequirement:
    requires_operator: bool = False
    requires_provider: bool = False
    requires_live_read: bool = False
    requires_output_quality: bool = False
    requires_broker: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "requires_operator": self.requires_operator,
            "requires_provider": self.requires_provider,
            "requires_live_read": self.requires_live_read,
            "requires_output_quality": self.requires_output_quality,
            "requires_broker": self.requires_broker,
        }


@dataclass
class CapabilityAction:
    action_id: str
    internal_only: bool
    external_side_effect: bool
    requires_operator: bool
    requires_provider: bool
    requires_live_read: bool
    requires_output_quality: bool
    requires_broker: bool
    enabled_by_default: bool
    phase_allowed: int
    description: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "internal_only": self.internal_only,
            "external_side_effect": self.external_side_effect,
            "requires_operator": self.requires_operator,
            "requires_provider": self.requires_provider,
            "requires_live_read": self.requires_live_read,
            "requires_output_quality": self.requires_output_quality,
            "requires_broker": self.requires_broker,
            "enabled_by_default": self.enabled_by_default,
            "phase_allowed": self.phase_allowed,
            "description": self.description,
        }


@dataclass
class CapabilityPolicy:
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    browser_side_effects_allowed: bool = False
    hardware_actuation_allowed: bool = False
    unknown_actions_allowed: bool = False
    disabled_actions_allowed: bool = False
    operator_absence_expands_authority: bool = False
    fixture_runtime_truth_allowed: bool = False
    dry_run_action_admission_allowed: bool = False
    provider_unavailable_blocks_provider_required_actions: bool = True
    live_read_unavailable_blocks_read_required_actions: bool = True
    stop_panic_blocks_all_non_emergency_actions: bool = True
    decision_receipt_required: bool = True
    decision_hash_required: bool = True
    hidden_chain_of_thought_storage_allowed: bool = False
    secret_storage_allowed: bool = False
    policy_refs: list[str] = field(default_factory=lambda: ["configs/agent_zero/capability_broker_policy.json"])

    def to_payload(self) -> dict[str, Any]:
        return {
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "browser_side_effects_allowed": self.browser_side_effects_allowed,
            "hardware_actuation_allowed": self.hardware_actuation_allowed,
            "unknown_actions_allowed": self.unknown_actions_allowed,
            "disabled_actions_allowed": self.disabled_actions_allowed,
            "operator_absence_expands_authority": self.operator_absence_expands_authority,
            "fixture_runtime_truth_allowed": self.fixture_runtime_truth_allowed,
            "dry_run_action_admission_allowed": self.dry_run_action_admission_allowed,
            "provider_unavailable_blocks_provider_required_actions": self.provider_unavailable_blocks_provider_required_actions,
            "live_read_unavailable_blocks_read_required_actions": self.live_read_unavailable_blocks_read_required_actions,
            "stop_panic_blocks_all_non_emergency_actions": self.stop_panic_blocks_all_non_emergency_actions,
            "decision_receipt_required": self.decision_receipt_required,
            "decision_hash_required": self.decision_hash_required,
            "hidden_chain_of_thought_storage_allowed": self.hidden_chain_of_thought_storage_allowed,
            "secret_storage_allowed": self.secret_storage_allowed,
            "policy_refs": list(self.policy_refs),
        }

    def policy_hash(self) -> str:
        return hash_record(self.to_payload())


@dataclass
class BrokerRequest:
    request_id: str
    agent_id: str
    turn_index: int
    turn_intent_ref: str
    turn_intent: TurnIntent
    agent_state_ref: str
    agent_state: AgentState
    observe_snapshot_ref: str
    observe_snapshot: ObserveSnapshot
    capability_menu_ref: str
    capability_menu: CapabilityMenuSnapshot
    runtime_mode: str
    operator_presence: str
    created_at: str
    hash: str = ""
    run_id: str | None = None
    provider_receipt_refs: list[str] = field(default_factory=list)
    live_read_receipt_refs: list[str] = field(default_factory=list)
    witness_receipt_refs: list[str] = field(default_factory=list)
    failure_posture_refs: list[str] = field(default_factory=list)
    scope_request_refs: list[str] = field(default_factory=list)
    stop_panic_state: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "turn_intent_ref": self.turn_intent_ref,
            "turn_intent": self.turn_intent.to_payload(),
            "agent_state_ref": self.agent_state_ref,
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "capability_menu_ref": self.capability_menu_ref,
            "runtime_mode": self.runtime_mode,
            "operator_presence": self.operator_presence,
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
            "witness_receipt_refs": list(self.witness_receipt_refs),
            "failure_posture_refs": list(self.failure_posture_refs),
            "scope_request_refs": list(self.scope_request_refs),
            "stop_panic_state": dict(self.stop_panic_state),
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> BrokerRequest:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return BrokerRequest(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class BrokerDecision:
    decision_id: str
    request_id: str
    agent_id: str
    turn_index: int
    chosen_action: str
    status: BrokerDecisionStatus
    admitted: bool
    refused: bool
    deferred: bool
    internal_only: bool
    external_side_effect: bool
    refusal_reasons: list[str]
    requirements_checked: dict[str, Any]
    policy_refs: list[str]
    created_at: str
    verdict: BrokerVerdict
    hash: str = ""
    run_id: str | None = None
    dispatch_plan_ref: str | None = None
    operator_question_refs: list[str] = field(default_factory=list)
    scope_request_refs: list[str] = field(default_factory=list)
    witness_receipt_ref: str | None = None
    failure_posture_ref: str | None = None
    previous_decision_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "chosen_action": self.chosen_action,
            "status": self.status.value,
            "admitted": self.admitted,
            "refused": self.refused,
            "deferred": self.deferred,
            "internal_only": self.internal_only,
            "external_side_effect": self.external_side_effect,
            "dispatch_plan_ref": self.dispatch_plan_ref,
            "refusal_reasons": list(self.refusal_reasons),
            "operator_question_refs": list(self.operator_question_refs),
            "scope_request_refs": list(self.scope_request_refs),
            "witness_receipt_ref": self.witness_receipt_ref,
            "failure_posture_ref": self.failure_posture_ref,
            "requirements_checked": dict(self.requirements_checked),
            "policy_refs": list(self.policy_refs),
            "verdict": self.verdict.value,
            "created_at": self.created_at,
            "hash": self.hash,
            "previous_decision_hash": self.previous_decision_hash,
        }

    def with_hash(self) -> BrokerDecision:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return BrokerDecision(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class BrokerAuditRecord:
    record_id: str
    decision_id: str
    request_id: str
    agent_id: str
    turn_index: int
    chosen_action: str
    verdict: str
    status: str
    admitted: bool
    refused: bool
    refusal_reasons: list[str]
    created_at: str
    hash: str = ""
    previous_record_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "turn_index": self.turn_index,
            "chosen_action": self.chosen_action,
            "verdict": self.verdict,
            "status": self.status,
            "admitted": self.admitted,
            "refused": self.refused,
            "refusal_reasons": list(self.refusal_reasons),
            "created_at": self.created_at,
            "hash": self.hash,
            "previous_record_hash": self.previous_record_hash,
        }

    def with_hash(self) -> BrokerAuditRecord:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return BrokerAuditRecord(**{**self.__dict__, "hash": hash_record(body)})


def new_request_id() -> str:
    return f"broker-req-{uuid.uuid4().hex[:12]}"


def new_decision_id() -> str:
    return f"broker-dec-{uuid.uuid4().hex[:12]}"


def validate_broker_decision(decision: BrokerDecision) -> BrokerVerdict:
    payload = decision.to_payload()
    has_secret, has_cot = scan_broker_payload(payload)
    if has_secret:
        return BrokerVerdict.RED_BROKER_SECRET_LEAK
    if has_cot:
        return BrokerVerdict.RED_BROKER_COT_LEAK
    if not decision.chosen_action or not decision.decision_id:
        return BrokerVerdict.RED_BROKER_DECISION_EMPTY
    if not decision.hash or not verify_record_hash(
        {k: v for k, v in payload.items() if k != "hash"}, decision.hash
    ):
        return BrokerVerdict.RED_BROKER_DECISION_EMPTY
    if decision.external_side_effect:
        return BrokerVerdict.RED_BROKER_EXTERNAL_SIDE_EFFECT
    return decision.verdict


__all__ = [
    "BrokerAuditRecord",
    "BrokerDecision",
    "BrokerDecisionStatus",
    "BrokerRefusalReason",
    "BrokerRequest",
    "BrokerVerdict",
    "CapabilityAction",
    "CapabilityPolicy",
    "CapabilityRequirement",
    "new_decision_id",
    "new_request_id",
    "validate_broker_decision",
]
