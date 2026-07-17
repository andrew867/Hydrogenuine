"""AgentState — durable agent runtime state."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_state.types import AgentStateVerdict

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/turn_state_policy.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_turn_state_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


@dataclass
class AgentState:
    agent_id: str
    runtime_mode: str
    created_at: str
    updated_at: str
    turn_index: int = 0
    run_id: str | None = None
    last_turn_receipt_ref: str | None = None
    last_turn_hash: str | None = None
    state_hash: str = ""
    operator_presence_state: str = "operator_unknown"
    provider_status_refs: list[str] = field(default_factory=list)
    live_read_status_refs: list[str] = field(default_factory=list)
    witness_state_ref: str | None = None
    failure_posture_refs: list[str] = field(default_factory=list)
    scope_request_refs: list[str] = field(default_factory=list)
    open_thread_refs: list[str] = field(default_factory=list)
    memory_refs: list[str] = field(default_factory=list)
    capability_menu_ref: str | None = None
    budget_state: dict[str, Any] = field(default_factory=dict)
    stop_panic_state: dict[str, Any] = field(default_factory=dict)
    dirty_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "runtime_mode": self.runtime_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turn_index": self.turn_index,
            "last_turn_receipt_ref": self.last_turn_receipt_ref,
            "last_turn_hash": self.last_turn_hash,
            "state_hash": self.state_hash,
            "operator_presence_state": self.operator_presence_state,
            "provider_status_refs": list(self.provider_status_refs),
            "live_read_status_refs": list(self.live_read_status_refs),
            "witness_state_ref": self.witness_state_ref,
            "failure_posture_refs": list(self.failure_posture_refs),
            "scope_request_refs": list(self.scope_request_refs),
            "open_thread_refs": list(self.open_thread_refs),
            "memory_refs": list(self.memory_refs),
            "capability_menu_ref": self.capability_menu_ref,
            "budget_state": dict(self.budget_state),
            "stop_panic_state": dict(self.stop_panic_state),
            "dirty_reason": self.dirty_reason,
        }

    def with_hash(self) -> AgentState:
        body = {k: v for k, v in self.to_payload().items() if k != "state_hash"}
        digest = hash_record(body)
        return AgentState(**{**self.__dict__, "state_hash": digest})


def create_agent_state(
    *,
    agent_id: str,
    runtime_mode: str,
    run_id: str | None = None,
    operator_presence_state: str = "operator_unknown",
) -> tuple[AgentStateVerdict, AgentState]:
    """Create initial agent state with deterministic hash."""
    if not agent_id or not agent_id.strip():
        empty = AgentState(
            agent_id="",
            runtime_mode=runtime_mode or "",
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        return AgentStateVerdict.RED_AGENT_STATE_EMPTY, empty
    if not runtime_mode or not runtime_mode.strip():
        empty = AgentState(
            agent_id=agent_id,
            runtime_mode="",
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        return AgentStateVerdict.RED_AGENT_STATE_EMPTY, empty

    ts = _now_iso()
    state = AgentState(
        agent_id=agent_id.strip(),
        run_id=run_id,
        runtime_mode=runtime_mode.strip(),
        created_at=ts,
        updated_at=ts,
        turn_index=0,
        operator_presence_state=operator_presence_state,
        budget_state={"posts_remaining": 0, "turns_budget": None},
        stop_panic_state={"stop_available": True, "panic_available": True},
    ).with_hash()
    return validate_agent_state(state)


def validate_agent_state(state: AgentState) -> tuple[AgentStateVerdict, AgentState]:
    """Validate agent state invariants."""
    payload = state.to_payload()
    if not state.agent_id or not state.runtime_mode:
        return AgentStateVerdict.RED_AGENT_STATE_EMPTY, state
    has_secret, has_cot = scan_payload(payload)
    if has_secret:
        return AgentStateVerdict.RED_AGENT_STATE_SECRET_LEAK, state
    if has_cot:
        return AgentStateVerdict.RED_AGENT_STATE_COT_LEAK, state
    policy = load_turn_state_policy()
    if policy.get("fixture_runtime_state_allowed") is False:
        if state.runtime_mode == "fixture" and not state.dirty_reason:
            return AgentStateVerdict.RED_AGENT_STATE_FIXTURE_RUNTIME, state
    if not state.state_hash:
        return AgentStateVerdict.RED_AGENT_STATE_HASH_MISSING, state
    if not verify_record_hash({k: v for k, v in payload.items() if k != "state_hash"}, state.state_hash):
        return AgentStateVerdict.RED_AGENT_STATE_HASH_MISSING, state
    return AgentStateVerdict.GREEN_AGENT_STATE_VALID, state


def new_agent_id() -> str:
    return f"agent0-{uuid.uuid4().hex[:12]}"


__all__ = [
    "AgentState",
    "create_agent_state",
    "load_turn_state_policy",
    "new_agent_id",
    "validate_agent_state",
]
