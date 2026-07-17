"""Reasoning engine schemas."""

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
from hg_runtime.agent_zero_state.turn_intent import TurnIntent

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/reasoning_engine_policy.json"

ROLE_AGENT_TURN_DECISION = "AGENT_TURN_DECISION"


class ReasoningProviderMode(str, Enum):
    LIVE = "live"
    DRY_RUN = "dry_run"
    FIXTURE = "fixture"
    FALLBACK_STUB = "fallback_stub"
    PROOF_REPLAY = "proof_replay"
    UNAVAILABLE = "unavailable"
    TEST_DOUBLE = "test_double"


class ReasoningVerdict(str, Enum):
    GREEN_REASONING_INTENT_VALID = "GREEN_REASONING_INTENT_VALID"
    YELLOW_PROVIDER_UNAVAILABLE = "YELLOW_PROVIDER_UNAVAILABLE"
    YELLOW_REASONING_DEFERRED = "YELLOW_REASONING_DEFERRED"
    YELLOW_WITNESS_OR_REST_CHOSEN = "YELLOW_WITNESS_OR_REST_CHOSEN"
    YELLOW_SCOPE_REQUEST_CHOSEN = "YELLOW_SCOPE_REQUEST_CHOSEN"
    RED_REASONING_PROVIDER_RECEIPT_MISSING = "RED_REASONING_PROVIDER_RECEIPT_MISSING"
    RED_REASONING_DRY_RUN_USED = "RED_REASONING_DRY_RUN_USED"
    RED_REASONING_FIXTURE_USED = "RED_REASONING_FIXTURE_USED"
    RED_REASONING_FALLBACK_STUB_USED = "RED_REASONING_FALLBACK_STUB_USED"
    RED_REASONING_EMPTY_OUTPUT = "RED_REASONING_EMPTY_OUTPUT"
    RED_REASONING_INVALID_JSON = "RED_REASONING_INVALID_JSON"
    RED_REASONING_UNKNOWN_ACTION = "RED_REASONING_UNKNOWN_ACTION"
    RED_REASONING_ACTION_OUTSIDE_MENU = "RED_REASONING_ACTION_OUTSIDE_MENU"
    RED_REASONING_EXTERNAL_PERMISSION = "RED_REASONING_EXTERNAL_PERMISSION"
    RED_REASONING_COT_STORED = "RED_REASONING_COT_STORED"
    RED_REASONING_SECRET_STORED = "RED_REASONING_SECRET_STORED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_reasoning_engine_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


@dataclass
class ReasoningRequest:
    request_id: str
    agent_id: str
    turn_index: int
    agent_state_ref: str
    observe_snapshot_ref: str
    capability_menu_ref: str
    prompt_hash: str
    runtime_mode: str
    role: str
    created_at: str
    hash: str = ""
    run_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "agent_state_ref": self.agent_state_ref,
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "capability_menu_ref": self.capability_menu_ref,
            "prompt_hash": self.prompt_hash,
            "runtime_mode": self.runtime_mode,
            "role": self.role,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ReasoningRequest:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ReasoningRequest(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ReasoningContext:
    charter_text_hash: str
    observe_snapshot: ObserveSnapshot
    capability_menu: CapabilityMenuSnapshot
    agent_state_summary: dict[str, Any]
    provider_reality_refs: list[str] = field(default_factory=list)
    live_read_receipt_refs: list[str] = field(default_factory=list)
    witness_receipt_refs: list[str] = field(default_factory=list)
    failure_posture_refs: list[str] = field(default_factory=list)
    scope_request_refs: list[str] = field(default_factory=list)
    outer_enforcement_summary: dict[str, Any] = field(default_factory=dict)
    witness_extension_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "charter_text_hash": self.charter_text_hash,
            "witness_extension_hash": self.witness_extension_hash,
            "observe_snapshot": self.observe_snapshot.to_payload(),
            "capability_menu": self.capability_menu.to_payload(),
            "agent_state_summary": dict(self.agent_state_summary),
            "provider_reality_refs": list(self.provider_reality_refs),
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
            "witness_receipt_refs": list(self.witness_receipt_refs),
            "failure_posture_refs": list(self.failure_posture_refs),
            "scope_request_refs": list(self.scope_request_refs),
            "outer_enforcement_summary": dict(self.outer_enforcement_summary),
        }


@dataclass
class ReasoningResult:
    result_id: str
    request_id: str
    provider_receipt_ref: str
    turn_intent: TurnIntent
    reasoning_summary: str
    raw_model_output_hash: str
    parsed_output_hash: str
    verdict: ReasoningVerdict
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "provider_receipt_ref": self.provider_receipt_ref,
            "turn_intent": self.turn_intent.to_payload(),
            "reasoning_summary": self.reasoning_summary,
            "raw_model_output_hash": self.raw_model_output_hash,
            "parsed_output_hash": self.parsed_output_hash,
            "verdict": self.verdict.value,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ReasoningResult:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ReasoningResult(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ReasoningFailure:
    failure_id: str
    request_id: str
    failure_kind: str
    verdict: ReasoningVerdict
    reason: str
    created_at: str
    hash: str = ""
    provider_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "request_id": self.request_id,
            "provider_receipt_ref": self.provider_receipt_ref,
            "failure_kind": self.failure_kind,
            "verdict": self.verdict.value,
            "reason": self.reason,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ReasoningFailure:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ReasoningFailure(**{**self.__dict__, "hash": hash_record(body)})


def new_request_id() -> str:
    return f"reason-req-{uuid.uuid4().hex[:12]}"


def new_result_id() -> str:
    return f"reason-res-{uuid.uuid4().hex[:12]}"


def new_failure_id() -> str:
    return f"reason-fail-{uuid.uuid4().hex[:12]}"


def build_reasoning_request(
    *,
    agent_id: str,
    turn_index: int,
    agent_state_ref: str,
    observe_snapshot_ref: str,
    capability_menu_ref: str,
    prompt_hash: str,
    runtime_mode: str,
    run_id: str | None = None,
) -> ReasoningRequest:
    req = ReasoningRequest(
        request_id=new_request_id(),
        agent_id=agent_id,
        run_id=run_id,
        turn_index=turn_index,
        agent_state_ref=agent_state_ref,
        observe_snapshot_ref=observe_snapshot_ref,
        capability_menu_ref=capability_menu_ref,
        prompt_hash=prompt_hash,
        runtime_mode=runtime_mode,
        role=ROLE_AGENT_TURN_DECISION,
        created_at=_now_iso(),
    )
    return req.with_hash()


def validate_reasoning_result_hash(result: ReasoningResult) -> bool:
    payload = result.to_payload()
    return bool(result.hash) and verify_record_hash(
        {k: v for k, v in payload.items() if k != "hash"}, result.hash
    )


__all__ = [
    "POLICY_PATH",
    "ROLE_AGENT_TURN_DECISION",
    "ReasoningContext",
    "ReasoningFailure",
    "ReasoningProviderMode",
    "ReasoningRequest",
    "ReasoningResult",
    "ReasoningVerdict",
    "build_reasoning_request",
    "load_reasoning_engine_policy",
    "new_failure_id",
    "new_request_id",
    "new_result_id",
    "validate_reasoning_result_hash",
]
