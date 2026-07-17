"""Dry soak schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.dry_soak.errors import DrySoakConfigError

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/longer_dry_soak_policy.json"


class DrySoakVerdict(str, Enum):
    GREEN_DRY_SOAK_COMPLETE = "GREEN_DRY_SOAK_COMPLETE"
    YELLOW_DRY_SOAK_COMPLETED_WITH_PROVIDER_UNAVAILABLE = "YELLOW_DRY_SOAK_COMPLETED_WITH_PROVIDER_UNAVAILABLE"
    YELLOW_DRY_SOAK_COMPLETED_WITH_LIVE_READ_UNAVAILABLE = "YELLOW_DRY_SOAK_COMPLETED_WITH_LIVE_READ_UNAVAILABLE"
    YELLOW_DRY_SOAK_STOPPED_BY_OPERATOR = "YELLOW_DRY_SOAK_STOPPED_BY_OPERATOR"
    YELLOW_DRY_SOAK_RESOURCE_PRESSURE = "YELLOW_DRY_SOAK_RESOURCE_PRESSURE"
    YELLOW_DRY_SOAK_NO_ARTIFACTS_CREATED = "YELLOW_DRY_SOAK_NO_ARTIFACTS_CREATED"
    RED_DRY_SOAK_UNBOUNDED = "RED_DRY_SOAK_UNBOUNDED"
    RED_DRY_SOAK_LOCK_FAILURE = "RED_DRY_SOAK_LOCK_FAILURE"
    RED_DRY_SOAK_STOP_PANIC_FAILURE = "RED_DRY_SOAK_STOP_PANIC_FAILURE"
    RED_DRY_SOAK_EXTERNAL_SIDE_EFFECT = "RED_DRY_SOAK_EXTERNAL_SIDE_EFFECT"
    RED_DRY_SOAK_RECEIPT_GAP = "RED_DRY_SOAK_RECEIPT_GAP"
    RED_DRY_SOAK_REPLAY_FAILURE = "RED_DRY_SOAK_REPLAY_FAILURE"
    RED_DRY_SOAK_QUEUE_EXPLOSION = "RED_DRY_SOAK_QUEUE_EXPLOSION"
    RED_DRY_SOAK_DUPLICATE_CONTENT_SPIRAL = "RED_DRY_SOAK_DUPLICATE_CONTENT_SPIRAL"
    RED_DRY_SOAK_FIXTURE_REGRESSION = "RED_DRY_SOAK_FIXTURE_REGRESSION"
    RED_DRY_SOAK_SECRET_OR_COT_LEAK = "RED_DRY_SOAK_SECRET_OR_COT_LEAK"


class ReadinessVerdict(str, Enum):
    GREEN_READY_FOR_PHASE_13_DRY_AUTONOMOUS_LOOP_PLANNING = "GREEN_READY_FOR_PHASE_13_DRY_AUTONOMOUS_LOOP_PLANNING"
    YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS = "YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS"
    YELLOW_READY_WITH_SHORT_DURATION_ONLY = "YELLOW_READY_WITH_SHORT_DURATION_ONLY"
    RED_NOT_READY_FOR_PHASE_13 = "RED_NOT_READY_FOR_PHASE_13"


class DrySoakRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    PANIC = "panic"
    FAILED = "failed"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dry_soak_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


@dataclass
class DrySoakConfig:
    run_id: str
    agent_id: str
    target_duration_seconds: int = 1800
    max_duration_seconds: int = 3600
    target_turns: int = 12
    max_turns: int = 50
    turn_interval_seconds: float = 0.0
    allow_provider: bool = False
    allow_live_read: bool = False
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    fixture_mode_allowed: bool = False
    operator_present: bool = True
    resource_watchdog_enabled: bool = True
    duplication_watchdog_enabled: bool = True
    created_at: str = ""
    hash: str = ""
    stop_file_path: str | None = None
    panic_file_path: str | None = None
    runtime_mode: str = "local_dev"

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "target_duration_seconds": self.target_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "target_turns": self.target_turns,
            "max_turns": self.max_turns,
            "turn_interval_seconds": self.turn_interval_seconds,
            "allow_provider": self.allow_provider,
            "allow_live_read": self.allow_live_read,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "fixture_mode_allowed": self.fixture_mode_allowed,
            "operator_present": self.operator_present,
            "resource_watchdog_enabled": self.resource_watchdog_enabled,
            "duplication_watchdog_enabled": self.duplication_watchdog_enabled,
            "runtime_mode": self.runtime_mode,
            "stop_file_path": self.stop_file_path,
            "panic_file_path": self.panic_file_path,
            "created_at": self.created_at or now_iso(),
            "hash": self.hash,
        }

    def with_hash(self) -> DrySoakConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DrySoakConfig(**{**self.__dict__, "hash": hash_record(body)})


def validate_dry_soak_config(config: DrySoakConfig) -> DrySoakConfig:
    policy = load_dry_soak_policy()
    hard_duration = int(policy.get("max_duration_seconds_hard_cap_phase_12", 14400))
    hard_turns = int(policy.get("max_turns_hard_cap_phase_12", 200))

    if config.external_side_effects_allowed:
        raise DrySoakConfigError("external_side_effects_allowed must be false")
    if config.live_writes_allowed:
        raise DrySoakConfigError("live_writes_allowed must be false")
    if config.fixture_mode_allowed:
        raise DrySoakConfigError("fixture_mode_allowed must be false in Phase 12")
    if config.max_duration_seconds > hard_duration:
        raise DrySoakConfigError(f"max_duration_seconds exceeds hard cap {hard_duration}")
    if config.max_turns > hard_turns:
        raise DrySoakConfigError(f"max_turns exceeds hard cap {hard_turns}")
    if config.max_turns < 1:
        raise DrySoakConfigError("max_turns must be >= 1")
    if not config.run_id or not config.agent_id:
        raise DrySoakConfigError("run_id and agent_id required")

    if not config.created_at:
        config = DrySoakConfig(**{**config.__dict__, "created_at": now_iso()})
    if not config.hash:
        config = config.with_hash()
    body = {k: v for k, v in config.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, config.hash):
        raise DrySoakConfigError("config hash invalid")
    return config


@dataclass
class DrySoakFailureBudget:
    max_red_turns: int = 0
    max_missing_receipts: int = 0
    max_replay_failures: int = 0
    max_external_side_effects: int = 0
    max_fixture_runtime_truth_events: int = 0
    max_secret_or_cot_leaks: int = 0
    max_queue_growth_per_turn: int = 5
    max_duplicate_body_hash_rate: float = 0.25

    def to_payload(self) -> dict[str, Any]:
        return {
            "max_red_turns": self.max_red_turns,
            "max_missing_receipts": self.max_missing_receipts,
            "max_replay_failures": self.max_replay_failures,
            "max_external_side_effects": self.max_external_side_effects,
            "max_fixture_runtime_truth_events": self.max_fixture_runtime_truth_events,
            "max_secret_or_cot_leaks": self.max_secret_or_cot_leaks,
            "max_queue_growth_per_turn": self.max_queue_growth_per_turn,
            "max_duplicate_body_hash_rate": self.max_duplicate_body_hash_rate,
        }

    @classmethod
    def from_policy(cls) -> DrySoakFailureBudget:
        p = load_dry_soak_policy()
        return cls(
            max_red_turns=int(p.get("max_red_turns", 0)),
            max_missing_receipts=int(p.get("max_missing_receipts", 0)),
            max_replay_failures=int(p.get("max_replay_failures", 0)),
            max_external_side_effects=int(p.get("max_external_side_effects", 0)),
            max_fixture_runtime_truth_events=int(p.get("max_fixture_runtime_truth_events", 0)),
            max_secret_or_cot_leaks=int(p.get("max_secret_or_cot_leaks", 0)),
            max_queue_growth_per_turn=int(p.get("max_queue_growth_per_turn", 5)),
            max_duplicate_body_hash_rate=float(p.get("max_duplicate_body_hash_rate", 0.25)),
        )


@dataclass
class DrySoakTurnSummary:
    turn_index: int
    turn_receipt_ref: str | None
    verdict: str
    artifact_count: int = 0
    review_queue_count: int = 0
    created_at: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "turn_receipt_ref": self.turn_receipt_ref,
            "verdict": self.verdict,
            "artifact_count": self.artifact_count,
            "review_queue_count": self.review_queue_count,
            "created_at": self.created_at,
        }


@dataclass
class DrySoakResourceSnapshot:
    run_id: str
    turn_index: int
    observed_at: str
    artifact_count: int
    review_queue_count: int
    turn_duration_seconds: float
    disk_free_bytes: int | None
    verdict: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "observed_at": self.observed_at,
            "artifact_count": self.artifact_count,
            "review_queue_count": self.review_queue_count,
            "turn_duration_seconds": self.turn_duration_seconds,
            "disk_free_bytes": self.disk_free_bytes,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> DrySoakResourceSnapshot:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DrySoakResourceSnapshot(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class DrySoakDuplicationReport:
    run_id: str
    turn_index: int
    duplicate_body_hash_rate: float
    fixture_hits: list[str]
    repeated_hashes: list[str]
    verdict: str
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "duplicate_body_hash_rate": self.duplicate_body_hash_rate,
            "fixture_hits": list(self.fixture_hits),
            "repeated_hashes": list(self.repeated_hashes),
            "verdict": self.verdict,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> DrySoakDuplicationReport:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DrySoakDuplicationReport(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class DrySoakRun:
    run_id: str
    agent_id: str
    started_at: str
    status: DrySoakRunStatus
    config_hash: str
    turn_count: int
    turn_summaries: list[DrySoakTurnSummary]
    verdict: DrySoakVerdict
    hash: str = ""
    finished_at: str | None = None
    readiness_verdict: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status.value,
            "config_hash": self.config_hash,
            "turn_count": self.turn_count,
            "turn_summaries": [t.to_payload() for t in self.turn_summaries],
            "verdict": self.verdict.value,
            "readiness_verdict": self.readiness_verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> DrySoakRun:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DrySoakRun(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class DrySoakReadinessReport:
    run_id: str
    duration_seconds: float
    turn_count: int
    provider_status: str
    live_read_status: str
    replay_status: str
    artifact_count: int
    review_queue_count: int
    duplication_verdict: str
    resource_verdict: str
    failure_budget_verdict: str
    external_side_effects: bool
    dry_soak_verdict: str
    readiness_verdict: ReadinessVerdict
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "duration_seconds": self.duration_seconds,
            "turn_count": self.turn_count,
            "provider_status": self.provider_status,
            "live_read_status": self.live_read_status,
            "replay_status": self.replay_status,
            "artifact_count": self.artifact_count,
            "review_queue_count": self.review_queue_count,
            "duplication_verdict": self.duplication_verdict,
            "resource_verdict": self.resource_verdict,
            "failure_budget_verdict": self.failure_budget_verdict,
            "external_side_effects": self.external_side_effects,
            "dry_soak_verdict": self.dry_soak_verdict,
            "readiness_verdict": self.readiness_verdict.value,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> DrySoakReadinessReport:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DrySoakReadinessReport(**{**self.__dict__, "hash": hash_record(body)})


__all__ = [
    "DrySoakConfig",
    "DrySoakDuplicationReport",
    "DrySoakFailureBudget",
    "DrySoakReadinessReport",
    "DrySoakResourceSnapshot",
    "DrySoakRun",
    "DrySoakRunStatus",
    "DrySoakTurnSummary",
    "DrySoakVerdict",
    "ReadinessVerdict",
    "load_dry_soak_policy",
    "now_iso",
    "validate_dry_soak_config",
]
