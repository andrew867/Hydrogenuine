"""Hands-off session configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.hands_off_session.errors import HandsOffConfigError
from hg_runtime.hands_off_session.schema import HandsOffSessionVerdict, load_hands_off_policy, now_iso


@dataclass
class HandsOffSessionConfig:
    session_id: str
    agent_id: str
    objective_universe_ref: str
    foreground_required: bool = True
    manual_stop_required: bool = True
    panic_required: bool = True
    scheduler_allowed: bool = False
    daemon_allowed: bool = False
    service_allowed: bool = False
    cron_allowed: bool = False
    fixed_turn_cap: int | None = None
    fixed_duration_cap: float | None = None
    turn_interval_seconds: float = 0.05
    resource_budget_ref: str = "configs/agent_zero/hands_off_session_policy.json"
    failure_budget_ref: str = "configs/agent_zero/hands_off_session_policy.json"
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    created_at: str = ""
    hash: str | None = None
    allow_provider: bool = False
    allow_live_read: bool = False
    test_only_stop_after_observed_turns: int | None = None
    governed_work_loop_enabled: bool = False
    work_envelope_ref: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "objective_universe_ref": self.objective_universe_ref,
            "foreground_required": self.foreground_required,
            "manual_stop_required": self.manual_stop_required,
            "panic_required": self.panic_required,
            "scheduler_allowed": self.scheduler_allowed,
            "daemon_allowed": self.daemon_allowed,
            "service_allowed": self.service_allowed,
            "cron_allowed": self.cron_allowed,
            "fixed_turn_cap": self.fixed_turn_cap,
            "fixed_duration_cap": self.fixed_duration_cap,
            "turn_interval_seconds": self.turn_interval_seconds,
            "resource_budget_ref": self.resource_budget_ref,
            "failure_budget_ref": self.failure_budget_ref,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "created_at": self.created_at,
            "hash": self.hash,
            "test_only_stop_after_observed_turns": self.test_only_stop_after_observed_turns,
            "governed_work_loop_enabled": self.governed_work_loop_enabled,
            "work_envelope_ref": self.work_envelope_ref,
        }

    def with_hash(self) -> HandsOffSessionConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return HandsOffSessionConfig(**{**self.__dict__, "hash": compute_record_hash(body)})


def validate_session_config(config: HandsOffSessionConfig, *, production_mode: bool = True) -> HandsOffSessionConfig:
    import os

    policy = load_hands_off_policy()
    errors: list[str] = []

    scoped_live = False
    soak_id = os.environ.get("HG_REAL_SOAK_SOAK_ID")
    if soak_id:
        from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope

        armed = load_armed_envelope(soak_id)
        live_env = (
            os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() == "true"
            or os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower() == "true"
        )
        scoped_live = bool(
            live_env and armed and armed.max_live_posts > 0 and armed.is_armed() and not armed.is_expired()
        )

    if production_mode and config.fixed_turn_cap is not None:
        errors.append(HandsOffSessionVerdict.RED_FIXED_TURN_CAP.value)
    if production_mode and config.fixed_duration_cap is not None:
        errors.append(HandsOffSessionVerdict.RED_FIXED_DURATION_CAP.value)
    if config.scheduler_allowed:
        errors.append(HandsOffSessionVerdict.RED_SCHEDULER.value)
    if config.daemon_allowed:
        errors.append(HandsOffSessionVerdict.RED_DAEMON.value)
    if config.service_allowed:
        errors.append(HandsOffSessionVerdict.RED_DAEMON.value)
    if config.cron_allowed:
        errors.append(HandsOffSessionVerdict.RED_SCHEDULER.value)
    if not config.manual_stop_required:
        errors.append(HandsOffSessionVerdict.RED_STOP_UNAVAILABLE.value)
    if not config.panic_required:
        errors.append(HandsOffSessionVerdict.RED_PANIC_UNAVAILABLE.value)
    if not config.foreground_required:
        errors.append("RED_PHASE22_BACKGROUND_PROCESS_SURVIVES_STOP")
    if config.external_side_effects_allowed and not policy.get("external_side_effects_allowed", False) and not scoped_live:
        errors.append(HandsOffSessionVerdict.RED_EXTERNAL_SIDE_EFFECT.value)
    if config.live_writes_allowed and not scoped_live:
        errors.append(HandsOffSessionVerdict.RED_EXTERNAL_SIDE_EFFECT.value)

    if errors:
        raise HandsOffConfigError(errors[0])

    if not config.created_at:
        config = HandsOffSessionConfig(**{**config.__dict__, "created_at": now_iso()})
    return config.with_hash()


def build_default_config(*, session_id: str, agent_id: str = "zero", universe_ref: str = "") -> HandsOffSessionConfig:
    return validate_session_config(
        HandsOffSessionConfig(
            session_id=session_id,
            agent_id=agent_id,
            objective_universe_ref=universe_ref,
            created_at=now_iso(),
        )
    )
