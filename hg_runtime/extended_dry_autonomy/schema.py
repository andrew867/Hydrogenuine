"""Extended dry autonomy schemas."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyConfigError

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/extended_dry_autonomy_policy.json"


class ExtendedDryAutonomyVerdict(str, Enum):
    GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE = "GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE"
    YELLOW_EXTENDED_DRY_AUTONOMY_PROVIDER_UNAVAILABLE = "YELLOW_EXTENDED_DRY_AUTONOMY_PROVIDER_UNAVAILABLE"
    YELLOW_EXTENDED_DRY_AUTONOMY_LIVE_READ_UNAVAILABLE = "YELLOW_EXTENDED_DRY_AUTONOMY_LIVE_READ_UNAVAILABLE"
    YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR = "YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR"
    YELLOW_EXTENDED_DRY_AUTONOMY_PAUSED_AND_RESUMED = "YELLOW_EXTENDED_DRY_AUTONOMY_PAUSED_AND_RESUMED"
    YELLOW_EXTENDED_DRY_AUTONOMY_RESOURCE_THROTTLED = "YELLOW_EXTENDED_DRY_AUTONOMY_RESOURCE_THROTTLED"
    YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"
    YELLOW_REMOTE_ANCHOR_NOT_ENABLED_BY_OPERATOR_ENV = "YELLOW_REMOTE_ANCHOR_NOT_ENABLED_BY_OPERATOR_ENV"
    RED_EXTENDED_DRY_AUTONOMY_UNBOUNDED = "RED_EXTENDED_DRY_AUTONOMY_UNBOUNDED"
    RED_EXTENDED_DRY_AUTONOMY_LOCK_FAILURE = "RED_EXTENDED_DRY_AUTONOMY_LOCK_FAILURE"
    RED_EXTENDED_DRY_AUTONOMY_OVERLAP = "RED_EXTENDED_DRY_AUTONOMY_OVERLAP"
    RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE = "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE"
    RED_EXTENDED_DRY_AUTONOMY_RESUME_FAILURE = "RED_EXTENDED_DRY_AUTONOMY_RESUME_FAILURE"
    RED_EXTENDED_DRY_AUTONOMY_STOP_PANIC_FAILURE = "RED_EXTENDED_DRY_AUTONOMY_STOP_PANIC_FAILURE"
    RED_EXTENDED_DRY_AUTONOMY_EXTERNAL_SIDE_EFFECT = "RED_EXTENDED_DRY_AUTONOMY_EXTERNAL_SIDE_EFFECT"
    RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP = "RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP"
    RED_EXTENDED_DRY_AUTONOMY_REPLAY_FAILURE = "RED_EXTENDED_DRY_AUTONOMY_REPLAY_FAILURE"
    RED_EXTENDED_DRY_AUTONOMY_QUEUE_EXPLOSION = "RED_EXTENDED_DRY_AUTONOMY_QUEUE_EXPLOSION"
    RED_EXTENDED_DRY_AUTONOMY_DUPLICATE_CONTENT_SPIRAL = "RED_EXTENDED_DRY_AUTONOMY_DUPLICATE_CONTENT_SPIRAL"
    RED_EXTENDED_DRY_AUTONOMY_FIXTURE_REGRESSION = "RED_EXTENDED_DRY_AUTONOMY_FIXTURE_REGRESSION"
    RED_EXTENDED_DRY_AUTONOMY_SECRET_OR_COT_LEAK = "RED_EXTENDED_DRY_AUTONOMY_SECRET_OR_COT_LEAK"
    RED_EXTENDED_DRY_AUTONOMY_BACKGROUND_PROCESS_LEFT_RUNNING = "RED_EXTENDED_DRY_AUTONOMY_BACKGROUND_PROCESS_LEFT_RUNNING"
    RED_EXTENDED_DRY_AUTONOMY_REMOTE_ANCHOR_FALSE_GREEN = "RED_EXTENDED_DRY_AUTONOMY_REMOTE_ANCHOR_FALSE_GREEN"


class ExtendedDryAutonomyState(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    PANIC = "panic"
    COMPLETED = "completed"
    FAILED = "failed"


class ReadinessVerdict(str, Enum):
    GREEN_READY_FOR_PHASE_15_LIVE_PROVIDER_DRY_AUTONOMY = "GREEN_READY_FOR_PHASE_15_LIVE_PROVIDER_DRY_AUTONOMY"
    YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS = "YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS"
    YELLOW_READY_FOR_LOCAL_ONLY_DRY_AUTONOMY = "YELLOW_READY_FOR_LOCAL_ONLY_DRY_AUTONOMY"
    RED_NOT_READY_FOR_PHASE_15 = "RED_NOT_READY_FOR_PHASE_15"


class PauseState(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    RESUMED = "resumed"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def _remote_push_allowed_by_env() -> bool:
    from hg_runtime.lifecycle_anchor_autopilot.push_resolver import resolve_lifecycle_push_policy

    return resolve_lifecycle_push_policy().push_requested


@dataclass
class ExtendedDryAutonomyConfig:
    run_id: str
    agent_id: str
    max_iterations: int = 20
    max_duration_seconds: int = 3600
    turn_interval_seconds: float = 60.0
    checkpoint_every_iterations: int = 5
    checkpoint_every_seconds: float = 900.0
    allow_provider: bool = False
    allow_live_read: bool = False
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    fixture_mode_allowed: bool = False
    operator_present: bool = True
    pause_file_path: str | None = None
    resume_file_path: str | None = None
    stop_file_path: str | None = None
    panic_file_path: str | None = None
    remote_anchor_push_allowed: bool = False
    created_at: str = ""
    hash: str = ""
    runtime_mode: str = "local_dev"

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "max_iterations": self.max_iterations,
            "max_duration_seconds": self.max_duration_seconds,
            "turn_interval_seconds": self.turn_interval_seconds,
            "checkpoint_every_iterations": self.checkpoint_every_iterations,
            "checkpoint_every_seconds": self.checkpoint_every_seconds,
            "allow_provider": self.allow_provider,
            "allow_live_read": self.allow_live_read,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "fixture_mode_allowed": self.fixture_mode_allowed,
            "operator_present": self.operator_present,
            "pause_file_path": self.pause_file_path,
            "resume_file_path": self.resume_file_path,
            "stop_file_path": self.stop_file_path,
            "panic_file_path": self.panic_file_path,
            "remote_anchor_push_allowed": self.remote_anchor_push_allowed,
            "runtime_mode": self.runtime_mode,
            "created_at": self.created_at or now_iso(),
            "hash": self.hash,
        }

    def with_hash(self) -> ExtendedDryAutonomyConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExtendedDryAutonomyConfig(**{**self.__dict__, "hash": hash_record(body)})


def validate_config(config: ExtendedDryAutonomyConfig) -> ExtendedDryAutonomyConfig:
    policy = load_policy()
    hard_iters = int(policy.get("max_iterations_hard_cap_phase_14", 500))
    hard_duration = int(policy.get("max_duration_seconds_hard_cap_phase_14", 28800))
    min_interval = float(policy.get("min_turn_interval_seconds_phase_14", 5))

    if config.external_side_effects_allowed:
        raise ExtendedDryAutonomyConfigError("external_side_effects_allowed must be false")
    if config.live_writes_allowed:
        raise ExtendedDryAutonomyConfigError("live_writes_allowed must be false")
    if config.fixture_mode_allowed:
        raise ExtendedDryAutonomyConfigError("fixture_mode_allowed must be false in Phase 14")
    if config.max_iterations > hard_iters:
        raise ExtendedDryAutonomyConfigError(f"max_iterations exceeds hard cap {hard_iters}")
    if config.max_duration_seconds > hard_duration:
        raise ExtendedDryAutonomyConfigError(f"max_duration_seconds exceeds hard cap {hard_duration}")
    if config.turn_interval_seconds > 0 and config.turn_interval_seconds < min_interval:
        raise ExtendedDryAutonomyConfigError(f"turn_interval_seconds below minimum {min_interval}")
    if config.max_iterations < 1:
        raise ExtendedDryAutonomyConfigError("max_iterations must be >= 1")
    if not config.run_id or not config.agent_id:
        raise ExtendedDryAutonomyConfigError("run_id and agent_id required")

    remote_env = _remote_push_allowed_by_env()
    if config.remote_anchor_push_allowed and not remote_env:
        raise ExtendedDryAutonomyConfigError("remote_anchor_push_allowed requires operator env/config")

    if not config.created_at:
        config = ExtendedDryAutonomyConfig(**{**config.__dict__, "created_at": now_iso()})
    if not config.hash:
        config = config.with_hash()
    body = {k: v for k, v in config.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, config.hash):
        raise ExtendedDryAutonomyConfigError("config hash invalid")
    return config


@dataclass
class ExtendedDryAutonomyCheckpoint:
    checkpoint_id: str
    run_id: str
    iteration_index: int
    turn_result_ref: str | None
    state_hash: str
    journal_head_hash: str
    review_queue_hash: str
    artifact_manifest_hash: str
    heartbeat_hash: str
    boot_anchor_ref: str | None = None
    last_shutdown_anchor_ref: str | None = None
    created_at: str = ""
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "iteration_index": self.iteration_index,
            "turn_result_ref": self.turn_result_ref,
            "state_hash": self.state_hash,
            "journal_head_hash": self.journal_head_hash,
            "review_queue_hash": self.review_queue_hash,
            "artifact_manifest_hash": self.artifact_manifest_hash,
            "heartbeat_hash": self.heartbeat_hash,
            "boot_anchor_ref": self.boot_anchor_ref,
            "last_shutdown_anchor_ref": self.last_shutdown_anchor_ref,
            "created_at": self.created_at or now_iso(),
            "hash": self.hash,
        }

    def with_hash(self) -> ExtendedDryAutonomyCheckpoint:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExtendedDryAutonomyCheckpoint(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ExtendedDryAutonomyPauseState:
    run_id: str
    state: PauseState
    paused_at: str | None = None
    resumed_at: str | None = None
    checkpoint_id: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state.value,
            "paused_at": self.paused_at,
            "resumed_at": self.resumed_at,
            "checkpoint_id": self.checkpoint_id,
            "events": list(self.events),
        }


@dataclass
class LifecycleAnchorAudit:
    anchor_audit_id: str
    run_id: str
    boot_anchor_ref: str | None
    shutdown_anchor_ref: str | None = None
    panic_anchor_ref: str | None = None
    local_witness_journal_ref: str | None = None
    remote_push_attempted: bool = False
    remote_push_succeeded: bool = False
    remote_freshness_verified: bool = False
    verdict: str = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"
    created_at: str = ""
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "anchor_audit_id": self.anchor_audit_id,
            "run_id": self.run_id,
            "boot_anchor_ref": self.boot_anchor_ref,
            "shutdown_anchor_ref": self.shutdown_anchor_ref,
            "panic_anchor_ref": self.panic_anchor_ref,
            "local_witness_journal_ref": self.local_witness_journal_ref,
            "remote_push_attempted": self.remote_push_attempted,
            "remote_push_succeeded": self.remote_push_succeeded,
            "remote_freshness_verified": self.remote_freshness_verified,
            "verdict": self.verdict,
            "created_at": self.created_at or now_iso(),
            "hash": self.hash,
        }

    def with_hash(self) -> LifecycleAnchorAudit:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return LifecycleAnchorAudit(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ExtendedDryAutonomyEnduranceBudget:
    max_red_turns: int = 0
    max_missing_receipts: int = 0
    max_replay_failures: int = 0
    max_checkpoint_failures: int = 0
    max_external_side_effects: int = 0
    max_fixture_runtime_truth_events: int = 0
    max_secret_or_cot_leaks: int = 0
    max_queue_growth_per_turn: int = 5
    max_duplicate_body_hash_rate: float = 0.25
    max_stale_heartbeat_seconds: int = 180
    max_pause_resume_failures: int = 0
    max_remote_anchor_false_green: int = 0

    @classmethod
    def from_policy(cls) -> ExtendedDryAutonomyEnduranceBudget:
        p = load_policy()
        return cls(
            max_red_turns=int(p.get("max_red_turns", 0)),
            max_missing_receipts=int(p.get("max_missing_receipts", 0)),
            max_replay_failures=int(p.get("max_replay_failures", 0)),
            max_checkpoint_failures=int(p.get("max_checkpoint_failures", 0)),
            max_external_side_effects=int(p.get("max_external_side_effects", 0)),
            max_fixture_runtime_truth_events=int(p.get("max_fixture_runtime_truth_events", 0)),
            max_secret_or_cot_leaks=int(p.get("max_secret_or_cot_leaks", 0)),
            max_queue_growth_per_turn=int(p.get("max_queue_growth_per_turn", 5)),
            max_duplicate_body_hash_rate=float(p.get("max_duplicate_body_hash_rate", 0.25)),
            max_stale_heartbeat_seconds=int(p.get("max_stale_heartbeat_seconds", 180)),
            max_pause_resume_failures=int(p.get("max_pause_resume_failures", 0)),
            max_remote_anchor_false_green=int(p.get("max_remote_anchor_false_green", 0)),
        )

    def to_payload(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ExtendedDryAutonomyRun:
    run_id: str
    agent_id: str
    started_at: str
    status: ExtendedDryAutonomyState
    config_hash: str
    lock_ref: str
    iteration_count: int
    turn_result_refs: list[str]
    heartbeat_refs: list[str]
    checkpoint_refs: list[str]
    pause_resume_events: list[dict[str, Any]]
    stop_panic_events: list[dict[str, Any]]
    verdict: ExtendedDryAutonomyVerdict
    hash: str = ""
    finished_at: str | None = None
    postflight_ref: str | None = None
    anchor_audit_ref: str | None = None
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
            "turn_result_refs": list(self.turn_result_refs),
            "heartbeat_refs": list(self.heartbeat_refs),
            "checkpoint_refs": list(self.checkpoint_refs),
            "pause_resume_events": list(self.pause_resume_events),
            "stop_panic_events": list(self.stop_panic_events),
            "postflight_ref": self.postflight_ref,
            "anchor_audit_ref": self.anchor_audit_ref,
            "verdict": self.verdict.value,
            "readiness_verdict": self.readiness_verdict,
            "boot_anchor_ref": self.boot_anchor_ref,
            "shutdown_anchor_ref": self.shutdown_anchor_ref,
            "hash": self.hash,
        }

    def with_hash(self) -> ExtendedDryAutonomyRun:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExtendedDryAutonomyRun(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ExtendedDryAutonomyReadiness:
    run_id: str
    loop_verdict: str
    readiness_verdict: ReadinessVerdict
    provider_status: str
    live_read_status: str
    duration_seconds: float
    iteration_count: int
    anchor_audit_verdict: str
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
            "anchor_audit_verdict": self.anchor_audit_verdict,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ExtendedDryAutonomyReadiness:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExtendedDryAutonomyReadiness(**{**self.__dict__, "hash": hash_record(body)})


__all__ = [
    "ExtendedDryAutonomyCheckpoint",
    "ExtendedDryAutonomyConfig",
    "ExtendedDryAutonomyEnduranceBudget",
    "ExtendedDryAutonomyPauseState",
    "ExtendedDryAutonomyReadiness",
    "ExtendedDryAutonomyRun",
    "ExtendedDryAutonomyState",
    "ExtendedDryAutonomyVerdict",
    "LifecycleAnchorAudit",
    "PauseState",
    "ReadinessVerdict",
    "load_policy",
    "now_iso",
    "validate_config",
]
