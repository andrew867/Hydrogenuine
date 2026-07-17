"""Agent turn engine schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_turn_engine.errors import AgentTurnValidationError

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/agent_turn_engine_policy.json"

PHASE_8_IMPLEMENTED_ACTIONS = frozenset({
    "rest_turn",
    "witness_turn",
    "request_more_scope",
    "propose_operator_question",
    "observe_social",
})

PHASE_9_CONTENT_ACTIONS = frozenset({
    "synthesize_notes",
    "propose_draft",
    "continue_prior_thread",
})

PHASE_9_IMPLEMENTED_ACTIONS = PHASE_8_IMPLEMENTED_ACTIONS | PHASE_9_CONTENT_ACTIONS

CONTENT_ACTIONS_DISABLED: frozenset[str] = frozenset()


class AgentTurnMode(str, Enum):
    LOCAL_DEV = "local_dev"
    PROOF = "proof"


class AgentTurnVerdict(str, Enum):
    GREEN_AGENT_TURN_COMPLETE_INTERNAL = "GREEN_AGENT_TURN_COMPLETE_INTERNAL"
    YELLOW_AGENT_TURN_RESTED = "YELLOW_AGENT_TURN_RESTED"
    YELLOW_AGENT_TURN_WITNESS_ONLY = "YELLOW_AGENT_TURN_WITNESS_ONLY"
    YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE = "YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE"
    YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE = "YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE"
    YELLOW_AGENT_TURN_OPERATOR_ABSENT = "YELLOW_AGENT_TURN_OPERATOR_ABSENT"
    YELLOW_AGENT_TURN_SCOPE_REQUESTED = "YELLOW_AGENT_TURN_SCOPE_REQUESTED"
    RED_AGENT_TURN_EMPTY = "RED_AGENT_TURN_EMPTY"
    RED_AGENT_TURN_NO_RECEIPT = "RED_AGENT_TURN_NO_RECEIPT"
    RED_AGENT_TURN_BROKER_BYPASS = "RED_AGENT_TURN_BROKER_BYPASS"
    RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT = "RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT"
    RED_AGENT_TURN_FIXTURE_RUNTIME = "RED_AGENT_TURN_FIXTURE_RUNTIME"
    RED_AGENT_TURN_COT_STORED = "RED_AGENT_TURN_COT_STORED"
    RED_AGENT_TURN_SECRET_STORED = "RED_AGENT_TURN_SECRET_STORED"
    RED_AGENT_TURN_REPLAY_FAILED = "RED_AGENT_TURN_REPLAY_FAILED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_agent_turn_engine_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def new_request_id() -> str:
    return f"turn-req-{uuid.uuid4().hex[:12]}"


def new_result_id() -> str:
    return f"turn-res-{uuid.uuid4().hex[:12]}"


def new_failure_id() -> str:
    return f"turn-fail-{uuid.uuid4().hex[:12]}"


@dataclass
class AgentTurnStorageRefs:
    agent_state_path: str
    journal_path: str
    observe_snapshot_path: str | None = None
    capability_menu_path: str | None = None
    reasoning_path: str | None = None
    broker_path: str | None = None
    dispatch_path: str | None = None
    receipt_path: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_state_path": self.agent_state_path,
            "journal_path": self.journal_path,
            "observe_snapshot_path": self.observe_snapshot_path,
            "capability_menu_path": self.capability_menu_path,
            "reasoning_path": self.reasoning_path,
            "broker_path": self.broker_path,
            "dispatch_path": self.dispatch_path,
            "receipt_path": self.receipt_path,
        }


@dataclass
class AgentTurnRequest:
    request_id: str
    agent_id: str
    run_id: str
    runtime_mode: str
    operator_presence: str
    requested_at: str
    allow_live_read: bool = False
    allow_provider: bool = False
    allow_internal_dispatch: bool = True
    external_side_effects_allowed: bool = False
    hash: str = ""
    turn_index: int | None = None
    max_turn_duration_ms: int | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "runtime_mode": self.runtime_mode,
            "turn_index": self.turn_index,
            "operator_presence": self.operator_presence,
            "requested_at": self.requested_at,
            "max_turn_duration_ms": self.max_turn_duration_ms,
            "allow_live_read": self.allow_live_read,
            "allow_provider": self.allow_provider,
            "allow_internal_dispatch": self.allow_internal_dispatch,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "hash": self.hash,
        }

    def with_hash(self) -> AgentTurnRequest:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return AgentTurnRequest(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class AgentTurnResult:
    result_id: str
    request_id: str
    agent_id: str
    run_id: str
    turn_index: int
    agent_state_ref: str
    observe_snapshot_ref: str
    capability_menu_ref: str
    broker_decision_ref: str
    turn_receipt_ref: str
    journal_ref: str
    state_after_ref: str
    verdict: AgentTurnVerdict
    created_at: str
    hash: str = ""
    reasoning_result_ref: str | None = None
    reasoning_failure_ref: str | None = None
    dispatch_result_ref: str | None = None
    storage_refs: AgentTurnStorageRefs | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "agent_state_ref": self.agent_state_ref,
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "capability_menu_ref": self.capability_menu_ref,
            "reasoning_result_ref": self.reasoning_result_ref,
            "reasoning_failure_ref": self.reasoning_failure_ref,
            "broker_decision_ref": self.broker_decision_ref,
            "dispatch_result_ref": self.dispatch_result_ref,
            "turn_receipt_ref": self.turn_receipt_ref,
            "journal_ref": self.journal_ref,
            "state_after_ref": self.state_after_ref,
            "verdict": self.verdict.value,
            "storage_refs": self.storage_refs.to_payload() if self.storage_refs else None,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> AgentTurnResult:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return AgentTurnResult(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class AgentTurnFailure:
    failure_id: str
    request_id: str
    failure_stage: str
    reason: str
    verdict: AgentTurnVerdict
    created_at: str
    hash: str = ""
    partial_refs: dict[str, str] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "request_id": self.request_id,
            "failure_stage": self.failure_stage,
            "reason": self.reason,
            "partial_refs": dict(self.partial_refs),
            "verdict": self.verdict.value,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> AgentTurnFailure:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return AgentTurnFailure(**{**self.__dict__, "hash": hash_record(body)})


def validate_agent_turn_request(request: AgentTurnRequest) -> AgentTurnRequest:
    policy = load_agent_turn_engine_policy()
    if request.external_side_effects_allowed:
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT.value)
    if request.runtime_mode == "fixture" and not policy.get("fixture_runtime_truth_allowed", False):
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME.value)
    if not request.agent_id or not request.run_id:
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_EMPTY.value)
    if not request.hash:
        request = request.with_hash()
    body = {k: v for k, v in request.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, request.hash):
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_EMPTY.value)
    return request


def build_agent_turn_request(
    *,
    agent_id: str,
    run_id: str,
    runtime_mode: str = "local_dev",
    operator_presence: str = "operator_present",
    allow_live_read: bool = False,
    allow_provider: bool = False,
    turn_index: int | None = None,
) -> AgentTurnRequest:
    return AgentTurnRequest(
        request_id=new_request_id(),
        agent_id=agent_id,
        run_id=run_id,
        runtime_mode=runtime_mode,
        operator_presence=operator_presence,
        requested_at=_now_iso(),
        allow_live_read=allow_live_read,
        allow_provider=allow_provider,
        turn_index=turn_index,
    ).with_hash()


__all__ = [
    "CONTENT_ACTIONS_DISABLED",
    "PHASE_8_IMPLEMENTED_ACTIONS",
    "AgentTurnFailure",
    "AgentTurnMode",
    "AgentTurnRequest",
    "AgentTurnResult",
    "AgentTurnStorageRefs",
    "AgentTurnVerdict",
    "build_agent_turn_request",
    "load_agent_turn_engine_policy",
    "new_failure_id",
    "new_request_id",
    "new_result_id",
    "validate_agent_turn_request",
]
