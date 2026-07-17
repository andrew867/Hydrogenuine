"""YSR state model — posture reset only, not truth."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

YSR_CYCLE_STATES = (
    "IDLE",
    "YAWN_REQUESTED",
    "PAUSING",
    "SCRATCH_SNAPSHOT_RECORDED",
    "SCRATCH_CLEARED",
    "EVENT_HEAD_READ",
    "WORLD_STATE_REFRESHED",
    "MEMORY_REFS_REFRESHED",
    "RESYNC_VERIFIED",
    "RESUMED",
    "NO_OP_ALREADY_SYNCED",
    "REFUSED",
    "ESCALATED_TO_CRR",
    "FAILED",
)

YawnTriggerResult = Literal[
    "yawn_allowed",
    "yawn_refused",
    "escalate_to_crr",
    "no_op_already_synced",
]


@dataclass(frozen=True)
class YawnRequest:
    agent_id: str
    reason_code: str
    operator_requested: bool = False
    event_lag_count: int = 0
    scratch_age_seconds: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "reason_code": self.reason_code,
            "operator_requested": self.operator_requested,
            "event_lag_count": self.event_lag_count,
            "scratch_age_seconds": self.scratch_age_seconds,
        }


@dataclass(frozen=True)
class YawnDecision:
    result: YawnTriggerResult
    reason_code: str
    agent_id: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "reason_code": self.reason_code,
            "agent_id": self.agent_id,
        }


@dataclass(frozen=True)
class ScratchSnapshot:
    agent_id: str
    scratch_hash: str
    event_head_seq: int | None
    keys_present: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "scratch_hash": self.scratch_hash,
            "event_head_seq": self.event_head_seq,
            "keys_present": list(self.keys_present),
        }


@dataclass
class YawnCycle:
    cycle_id: str
    agent_id: str
    requested_at: str
    reason_code: str = ""
    prior_event_head: int | None = None
    current_event_head: int | None = None
    event_lag_count: int = 0
    prior_world_state_hash: str | None = None
    refreshed_world_state_hash: str | None = None
    scratch_hash_before: str | None = None
    scratch_cleared_keys: list[str] = field(default_factory=list)
    memory_refs_refreshed: list[str] = field(default_factory=list)
    result_status: str = "IDLE"
    completed_at: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "agent_id": self.agent_id,
            "requested_at": self.requested_at,
            "reason_code": self.reason_code,
            "prior_event_head": self.prior_event_head,
            "current_event_head": self.current_event_head,
            "event_lag_count": self.event_lag_count,
            "prior_world_state_hash": self.prior_world_state_hash,
            "refreshed_world_state_hash": self.refreshed_world_state_hash,
            "scratch_hash_before": self.scratch_hash_before,
            "scratch_cleared_keys": list(self.scratch_cleared_keys),
            "memory_refs_refreshed": list(self.memory_refs_refreshed),
            "result_status": self.result_status,
            "completed_at": self.completed_at,
        }


@dataclass(frozen=True)
class ResyncResult:
    ok: bool
    prior_event_head: int | None
    current_event_head: int | None
    prior_world_state_hash: str
    refreshed_world_state_hash: str
    event_log_mutated: bool = False
    authority_freshened: bool = False
    receipts_deleted: bool = False
    stale_proposals_invalidated: int = 0
    reason_code: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "prior_event_head": self.prior_event_head,
            "current_event_head": self.current_event_head,
            "prior_world_state_hash": self.prior_world_state_hash,
            "refreshed_world_state_hash": self.refreshed_world_state_hash,
            "event_log_mutated": self.event_log_mutated,
            "authority_freshened": self.authority_freshened,
            "receipts_deleted": self.receipts_deleted,
            "stale_proposals_invalidated": self.stale_proposals_invalidated,
            "reason_code": self.reason_code,
            "observation_only": True,
        }


__all__ = [
    "YSR_CYCLE_STATES",
    "ResyncResult",
    "ScratchSnapshot",
    "YawnCycle",
    "YawnDecision",
    "YawnRequest",
    "YawnTriggerResult",
]
