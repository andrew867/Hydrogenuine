"""Dry autonomous loop schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopConfigError

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/bounded_dry_autonomous_loop_policy.json"

ALLOWED_SCHEDULE_MODES = frozenset({"fixed_interval", "manual_step"})
FORBIDDEN_SCHEDULE_MODES = frozenset({"cron", "daemon", "service", "unbounded", "overnight", "continuous"})


class DryAutonomousLoopVerdict(str, Enum):
    GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE = "GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE"
    YELLOW_DRY_AUTONOMOUS_LOOP_COMPLETED_WITH_DEFERRED_TURNS = "YELLOW_DRY_AUTONOMOUS_LOOP_COMPLETED_WITH_DEFERRED_TURNS"
    YELLOW_DRY_AUTONOMOUS_LOOP_PROVIDER_UNAVAILABLE = "YELLOW_DRY_AUTONOMOUS_LOOP_PROVIDER_UNAVAILABLE"
    YELLOW_DRY_AUTONOMOUS_LOOP_LIVE_READ_UNAVAILABLE = "YELLOW_DRY_AUTONOMOUS_LOOP_LIVE_READ_UNAVAILABLE"
    YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR = "YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR"
    YELLOW_DRY_AUTONOMOUS_LOOP_RESOURCE_THROTTLED = "YELLOW_DRY_AUTONOMOUS_LOOP_RESOURCE_THROTTLED"
    RED_DRY_AUTONOMOUS_LOOP_UNBOUNDED = "RED_DRY_AUTONOMOUS_LOOP_UNBOUNDED"
    RED_DRY_AUTONOMOUS_LOOP_LOCK_FAILURE = "RED_DRY_AUTONOMOUS_LOOP_LOCK_FAILURE"
    RED_DRY_AUTONOMOUS_LOOP_OVERLAP = "RED_DRY_AUTONOMOUS_LOOP_OVERLAP"
    RED_DRY_AUTONOMOUS_LOOP_STOP_PANIC_FAILURE = "RED_DRY_AUTONOMOUS_LOOP_STOP_PANIC_FAILURE"
    RED_DRY_AUTONOMOUS_LOOP_EXTERNAL_SIDE_EFFECT = "RED_DRY_AUTONOMOUS_LOOP_EXTERNAL_SIDE_EFFECT"
    RED_DRY_AUTONOMOUS_LOOP_RECEIPT_GAP = "RED_DRY_AUTONOMOUS_LOOP_RECEIPT_GAP"
    RED_DRY_AUTONOMOUS_LOOP_REPLAY_FAILURE = "RED_DRY_AUTONOMOUS_LOOP_REPLAY_FAILURE"
    RED_DRY_AUTONOMOUS_LOOP_QUEUE_EXPLOSION = "RED_DRY_AUTONOMOUS_LOOP_QUEUE_EXPLOSION"
    RED_DRY_AUTONOMOUS_LOOP_DUPLICATE_CONTENT_SPIRAL = "RED_DRY_AUTONOMOUS_LOOP_DUPLICATE_CONTENT_SPIRAL"
    RED_DRY_AUTONOMOUS_LOOP_FIXTURE_REGRESSION = "RED_DRY_AUTONOMOUS_LOOP_FIXTURE_REGRESSION"
    RED_DRY_AUTONOMOUS_LOOP_SECRET_OR_COT_LEAK = "RED_DRY_AUTONOMOUS_LOOP_SECRET_OR_COT_LEAK"
    RED_DRY_AUTONOMOUS_LOOP_BACKGROUND_PROCESS_LEFT_RUNNING = "RED_DRY_AUTONOMOUS_LOOP_BACKGROUND_PROCESS_LEFT_RUNNING"


class DryAutonomousLoopState(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    PANIC = "panic"
    COMPLETED = "completed"
    FAILED = "failed"


class ReadinessVerdict(str, Enum):
    GREEN_READY_FOR_PHASE_14_EXTENDED_DRY_AUTONOMY = "GREEN_READY_FOR_PHASE_14_EXTENDED_DRY_AUTONOMY"
    YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS = "YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS"
    YELLOW_READY_ONLY_FOR_SHORT_BOUNDED_DRY_RUNS = "YELLOW_READY_ONLY_FOR_SHORT_BOUNDED_DRY_RUNS"
    RED_NOT_READY_FOR_PHASE_14 = "RED_NOT_READY_FOR_PHASE_14"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_loop_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


@dataclass
class DryAutonomousLoopConfig:
    run_id: str
    agent_id: str
    schedule_mode: str = "fixed_interval"
    max_iterations: int = 5
    max_duration_seconds: int = 900
    turn_interval_seconds: float = 60.0
    jitter_seconds: float = 0.0
    allow_provider: bool = False
    allow_live_read: bool = False
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    fixture_mode_allowed: bool = False
    operator_present: bool = True
    stop_file_path: str | None = None
    panic_file_path: str | None = None
    created_at: str = ""
    hash: str = ""
    runtime_mode: str = "local_dev"

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "schedule_mode": self.schedule_mode,
            "max_iterations": self.max_iterations,
            "max_duration_seconds": self.max_duration_seconds,
            "turn_interval_seconds": self.turn_interval_seconds,
            "jitter_seconds": self.jitter_seconds,
            "allow_provider": self.allow_provider,
            "allow_live_read": self.allow_live_read,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "fixture_mode_allowed": self.fixture_mode_allowed,
            "operator_present": self.operator_present,
            "stop_file_path": self.stop_file_path,
            "panic_file_path": self.panic_file_path,
            "runtime_mode": self.runtime_mode,
            "created_at": self.created_at or now_iso(),
            "hash": self.hash,
        }

    def with_hash(self) -> DryAutonomousLoopConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DryAutonomousLoopConfig(**{**self.__dict__, "hash": hash_record(body)})


def validate_loop_config(config: DryAutonomousLoopConfig) -> DryAutonomousLoopConfig:
    policy = load_loop_policy()
    hard_iters = int(policy.get("max_iterations_hard_cap_phase_13", 50))
    hard_duration = int(policy.get("max_duration_seconds_hard_cap_phase_13", 7200))
    min_interval = float(policy.get("min_turn_interval_seconds_phase_13", 5))

    if config.external_side_effects_allowed:
        raise DryAutonomousLoopConfigError("external_side_effects_allowed must be false")
    if config.live_writes_allowed:
        raise DryAutonomousLoopConfigError("live_writes_allowed must be false")
    if config.fixture_mode_allowed:
        raise DryAutonomousLoopConfigError("fixture_mode_allowed must be false in Phase 13")
    if config.schedule_mode in FORBIDDEN_SCHEDULE_MODES:
        raise DryAutonomousLoopConfigError(f"forbidden schedule_mode: {config.schedule_mode}")
    if config.schedule_mode not in ALLOWED_SCHEDULE_MODES:
        raise DryAutonomousLoopConfigError(f"schedule_mode not allowed: {config.schedule_mode}")
    if config.max_iterations > hard_iters:
        raise DryAutonomousLoopConfigError(f"max_iterations exceeds hard cap {hard_iters}")
    if config.max_duration_seconds > hard_duration:
        raise DryAutonomousLoopConfigError(f"max_duration_seconds exceeds hard cap {hard_duration}")
    if config.schedule_mode == "fixed_interval" and config.turn_interval_seconds < min_interval:
        raise DryAutonomousLoopConfigError(f"turn_interval_seconds below minimum {min_interval}")
    if config.max_iterations < 1:
        raise DryAutonomousLoopConfigError("max_iterations must be >= 1")
    if not config.run_id or not config.agent_id:
        raise DryAutonomousLoopConfigError("run_id and agent_id required")

    if not config.created_at:
        config = DryAutonomousLoopConfig(**{**config.__dict__, "created_at": now_iso()})
    if not config.hash:
        config = config.with_hash()
    body = {k: v for k, v in config.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, config.hash):
        raise DryAutonomousLoopConfigError("config hash invalid")
    return config


@dataclass
class DryAutonomousLoopIteration:
    iteration_index: int
    turn_receipt_ref: str | None
    turn_verdict: str
    created_at: str
    artifact_count: int = 0
    review_queue_count: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "iteration_index": self.iteration_index,
            "turn_receipt_ref": self.turn_receipt_ref,
            "turn_verdict": self.turn_verdict,
            "artifact_count": self.artifact_count,
            "review_queue_count": self.review_queue_count,
            "created_at": self.created_at,
        }


@dataclass
class DryAutonomousLoopRun:
    run_id: str
    agent_id: str
    started_at: str
    status: DryAutonomousLoopState
    config_hash: str
    lock_ref: str
    iteration_count: int
    iteration_refs: list[str]
    turn_result_refs: list[str]
    heartbeat_refs: list[str]
    stop_panic_events: list[dict[str, Any]]
    verdict: DryAutonomousLoopVerdict
    hash: str = ""
    finished_at: str | None = None
    postflight_ref: str | None = None
    readiness_verdict: str | None = None
    boot_anchor_ref: str | None = None
    shutdown_anchor_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status.value,
            "config_hash": self.config_hash,
            "lock_ref": self.lock_ref,
            "iteration_count": self.iteration_count,
            "iteration_refs": list(self.iteration_refs),
            "turn_result_refs": list(self.turn_result_refs),
            "heartbeat_refs": list(self.heartbeat_refs),
            "stop_panic_events": list(self.stop_panic_events),
            "postflight_ref": self.postflight_ref,
            "verdict": self.verdict.value,
            "readiness_verdict": self.readiness_verdict,
            "boot_anchor_ref": self.boot_anchor_ref,
            "shutdown_anchor_ref": self.shutdown_anchor_ref,
            "hash": self.hash,
        }

    def with_hash(self) -> DryAutonomousLoopRun:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DryAutonomousLoopRun(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class DryAutonomousLoopPostflight:
    run_id: str
    iteration_count: int
    duration_seconds: float
    replay_verdict: str
    external_side_effects: bool
    live_writes: bool
    lock_released: bool
    background_process_left: bool
    stop_events: int
    panic_events: int
    boot_anchor_committed: bool
    shutdown_anchor_committed: bool
    verdict: str
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "iteration_count": self.iteration_count,
            "duration_seconds": self.duration_seconds,
            "replay_verdict": self.replay_verdict,
            "external_side_effects": self.external_side_effects,
            "live_writes": self.live_writes,
            "lock_released": self.lock_released,
            "background_process_left": self.background_process_left,
            "stop_events": self.stop_events,
            "panic_events": self.panic_events,
            "boot_anchor_committed": self.boot_anchor_committed,
            "shutdown_anchor_committed": self.shutdown_anchor_committed,
            "verdict": self.verdict,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> DryAutonomousLoopPostflight:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DryAutonomousLoopPostflight(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class DryAutonomousLoopReadiness:
    run_id: str
    loop_verdict: str
    readiness_verdict: ReadinessVerdict
    provider_status: str
    live_read_status: str
    duration_seconds: float
    iteration_count: int
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "loop_verdict": self.loop_verdict,
            "readiness_verdict": self.readiness_verdict.value,
            "provider_status": self.provider_status,
            "live_read_status": self.live_read_status,
            "duration_seconds": self.duration_seconds,
            "iteration_count": self.iteration_count,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> DryAutonomousLoopReadiness:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DryAutonomousLoopReadiness(**{**self.__dict__, "hash": hash_record(body)})


__all__ = [
    "ALLOWED_SCHEDULE_MODES",
    "DryAutonomousLoopConfig",
    "DryAutonomousLoopIteration",
    "DryAutonomousLoopPostflight",
    "DryAutonomousLoopReadiness",
    "DryAutonomousLoopRun",
    "DryAutonomousLoopState",
    "DryAutonomousLoopVerdict",
    "FORBIDDEN_SCHEDULE_MODES",
    "ReadinessVerdict",
    "load_loop_policy",
    "now_iso",
    "validate_loop_config",
]
