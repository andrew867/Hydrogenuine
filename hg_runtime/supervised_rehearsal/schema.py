"""Supervised rehearsal schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.supervised_rehearsal.errors import RehearsalConfigError

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/supervised_rehearsal_policy.json"


class SupervisedRehearsalVerdict(str, Enum):
    GREEN_SUPERVISED_REHEARSAL_COMPLETE = "GREEN_SUPERVISED_REHEARSAL_COMPLETE"
    YELLOW_REHEARSAL_COMPLETED_WITH_DEFERRED_TURNS = "YELLOW_REHEARSAL_COMPLETED_WITH_DEFERRED_TURNS"
    YELLOW_REHEARSAL_STOPPED_BY_OPERATOR = "YELLOW_REHEARSAL_STOPPED_BY_OPERATOR"
    YELLOW_REHEARSAL_PROVIDER_UNAVAILABLE = "YELLOW_REHEARSAL_PROVIDER_UNAVAILABLE"
    YELLOW_REHEARSAL_LIVE_READ_UNAVAILABLE = "YELLOW_REHEARSAL_LIVE_READ_UNAVAILABLE"
    RED_REHEARSAL_UNBOUNDED = "RED_REHEARSAL_UNBOUNDED"
    RED_REHEARSAL_LOCK_MISSING = "RED_REHEARSAL_LOCK_MISSING"
    RED_REHEARSAL_LOCK_CONFLICT = "RED_REHEARSAL_LOCK_CONFLICT"
    RED_REHEARSAL_STOP_IGNORED = "RED_REHEARSAL_STOP_IGNORED"
    RED_REHEARSAL_PANIC_IGNORED = "RED_REHEARSAL_PANIC_IGNORED"
    RED_REHEARSAL_EXTERNAL_SIDE_EFFECT = "RED_REHEARSAL_EXTERNAL_SIDE_EFFECT"
    RED_REHEARSAL_TURN_FAILURE = "RED_REHEARSAL_TURN_FAILURE"
    RED_REHEARSAL_REPLAY_FAILURE = "RED_REHEARSAL_REPLAY_FAILURE"
    RED_REHEARSAL_RECEIPT_MISSING = "RED_REHEARSAL_RECEIPT_MISSING"


class RunLockState(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    STALE = "stale"
    MISSING = "missing"
    CONFLICT = "conflict"


class StopPanicState(str, Enum):
    AVAILABLE = "available"
    STOPPED = "stopped"
    PANIC = "panic"
    UNAVAILABLE = "unavailable"


class RehearsalRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    PANIC = "panic"
    FAILED = "failed"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_supervised_rehearsal_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


@dataclass
class SupervisedRehearsalConfig:
    run_id: str
    agent_id: str
    max_turns: int = 3
    max_duration_seconds: int = 300
    turn_interval_seconds: float = 0.0
    allow_live_read: bool = False
    allow_provider: bool = False
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    fixture_mode_allowed: bool = False
    operator_present: bool = True
    created_at: str = ""
    hash: str = ""
    stop_file_path: str | None = None
    panic_file_path: str | None = None
    runtime_mode: str = "local_dev"

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "max_turns": self.max_turns,
            "max_duration_seconds": self.max_duration_seconds,
            "turn_interval_seconds": self.turn_interval_seconds,
            "allow_live_read": self.allow_live_read,
            "allow_provider": self.allow_provider,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "fixture_mode_allowed": self.fixture_mode_allowed,
            "operator_present": self.operator_present,
            "runtime_mode": self.runtime_mode,
            "stop_file_path": self.stop_file_path,
            "panic_file_path": self.panic_file_path,
            "created_at": self.created_at or now_iso(),
            "hash": self.hash,
        }

    def with_hash(self) -> SupervisedRehearsalConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SupervisedRehearsalConfig(**{**self.__dict__, "hash": hash_record(body)})


def validate_rehearsal_config(config: SupervisedRehearsalConfig) -> SupervisedRehearsalConfig:
    policy = load_supervised_rehearsal_policy()
    hard_turns = int(policy.get("max_turns_hard_cap_phase_11", 10))
    hard_duration = int(policy.get("max_duration_seconds_hard_cap_phase_11", 1800))

    if config.external_side_effects_allowed:
        raise RehearsalConfigError("external_side_effects_allowed must be false")
    if config.live_writes_allowed:
        raise RehearsalConfigError("live_writes_allowed must be false")
    if config.fixture_mode_allowed:
        raise RehearsalConfigError("fixture_mode_allowed must be false in Phase 11")
    if config.max_turns > hard_turns:
        raise RehearsalConfigError(f"max_turns exceeds hard cap {hard_turns}")
    if config.max_duration_seconds > hard_duration:
        raise RehearsalConfigError(f"max_duration_seconds exceeds hard cap {hard_duration}")
    if config.max_turns < 1:
        raise RehearsalConfigError("max_turns must be >= 1")
    if not config.run_id or not config.agent_id:
        raise RehearsalConfigError("run_id and agent_id required")

    if not config.created_at:
        config = SupervisedRehearsalConfig(**{**config.__dict__, "created_at": now_iso()})
    if not config.hash:
        config = config.with_hash()
    body = {k: v for k, v in config.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, config.hash):
        raise RehearsalConfigError("config hash invalid")
    return config


@dataclass
class SupervisedRehearsalTurnSummary:
    turn_index: int
    turn_receipt_ref: str | None
    turn_result_ref: str | None
    verdict: str
    observe_snapshot_ref: str | None = None
    broker_decision_ref: str | None = None
    created_at: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "turn_receipt_ref": self.turn_receipt_ref,
            "turn_result_ref": self.turn_result_ref,
            "verdict": self.verdict,
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "broker_decision_ref": self.broker_decision_ref,
            "created_at": self.created_at,
        }


@dataclass
class SupervisedRehearsalRun:
    run_id: str
    agent_id: str
    started_at: str
    status: RehearsalRunStatus
    config_hash: str
    lock_ref: str
    turn_count: int
    turn_result_refs: list[str]
    stop_panic_events: list[dict[str, Any]]
    verdict: SupervisedRehearsalVerdict
    hash: str = ""
    finished_at: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status.value,
            "config_hash": self.config_hash,
            "lock_ref": self.lock_ref,
            "turn_count": self.turn_count,
            "turn_result_refs": list(self.turn_result_refs),
            "stop_panic_events": list(self.stop_panic_events),
            "verdict": self.verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> SupervisedRehearsalRun:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SupervisedRehearsalRun(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class PostflightSummary:
    run_id: str
    turn_count: int
    duration_seconds: float
    turn_receipts: list[str]
    journal_ref: str | None
    replay_verdict: str
    artifact_count: int
    review_candidate_count: int
    stop_events: int
    panic_events: int
    external_side_effects: bool
    live_writes: bool
    verdict: str
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "turn_count": self.turn_count,
            "duration_seconds": self.duration_seconds,
            "turn_receipts": list(self.turn_receipts),
            "journal_ref": self.journal_ref,
            "replay_verdict": self.replay_verdict,
            "artifact_count": self.artifact_count,
            "review_candidate_count": self.review_candidate_count,
            "stop_events": self.stop_events,
            "panic_events": self.panic_events,
            "external_side_effects": self.external_side_effects,
            "live_writes": self.live_writes,
            "verdict": self.verdict,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> PostflightSummary:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return PostflightSummary(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class SupervisedRehearsalResult:
    run_id: str
    agent_id: str
    started_at: str
    finished_at: str
    turn_count: int
    turn_summaries: list[SupervisedRehearsalTurnSummary]
    postflight_ref: str | None
    verdict: SupervisedRehearsalVerdict
    hash: str = ""
    run_status: str = ""
    deferred_turns: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "turn_count": self.turn_count,
            "turn_summaries": [t.to_payload() for t in self.turn_summaries],
            "postflight_ref": self.postflight_ref,
            "verdict": self.verdict.value,
            "run_status": self.run_status,
            "deferred_turns": self.deferred_turns,
            "hash": self.hash,
        }

    def with_hash(self) -> SupervisedRehearsalResult:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SupervisedRehearsalResult(**{**self.__dict__, "hash": hash_record(body)})


__all__ = [
    "PostflightSummary",
    "RehearsalRunStatus",
    "RunLockState",
    "StopPanicState",
    "SupervisedRehearsalConfig",
    "SupervisedRehearsalResult",
    "SupervisedRehearsalRun",
    "SupervisedRehearsalTurnSummary",
    "SupervisedRehearsalVerdict",
    "load_supervised_rehearsal_policy",
    "now_iso",
    "validate_rehearsal_config",
]
