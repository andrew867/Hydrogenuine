"""Overnight field run configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.errors import FieldRunConfigError
from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict, load_field_run_policy, now_iso


@dataclass
class OvernightFieldRunConfig:
    field_run_id: str
    agent_id: str
    hands_off_session_config_ref: str = ""
    governed_work_envelope_ref: str = ""
    objective_universe_ref: str = ""
    mode: str = FieldRunMode.OPERATOR_FIELD_RUN.value
    foreground_required: bool = True
    manual_stop_required: bool = True
    panic_required: bool = True
    scheduler_allowed: bool = False
    daemon_allowed: bool = False
    service_allowed: bool = False
    cron_allowed: bool = False
    fixed_turn_cap: int | None = None
    fixed_duration_cap: float | None = None
    operator_expected_sleep_window: str | None = None
    checkpoint_interval_turns: int = 5
    checkpoint_interval_seconds: float = 300.0
    external_side_effects_allowed: bool = False
    live_writes_allowed: bool = False
    turn_interval_seconds: float = 0.05
    test_only_stop_after_observed_turns: int | None = None
    created_at: str = ""
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "field_run_id": self.field_run_id,
            "agent_id": self.agent_id,
            "hands_off_session_config_ref": self.hands_off_session_config_ref,
            "governed_work_envelope_ref": self.governed_work_envelope_ref,
            "objective_universe_ref": self.objective_universe_ref,
            "mode": self.mode,
            "foreground_required": self.foreground_required,
            "manual_stop_required": self.manual_stop_required,
            "panic_required": self.panic_required,
            "scheduler_allowed": self.scheduler_allowed,
            "daemon_allowed": self.daemon_allowed,
            "service_allowed": self.service_allowed,
            "cron_allowed": self.cron_allowed,
            "fixed_turn_cap": self.fixed_turn_cap,
            "fixed_duration_cap": self.fixed_duration_cap,
            "operator_expected_sleep_window": self.operator_expected_sleep_window,
            "checkpoint_interval_turns": self.checkpoint_interval_turns,
            "checkpoint_interval_seconds": self.checkpoint_interval_seconds,
            "external_side_effects_allowed": self.external_side_effects_allowed,
            "live_writes_allowed": self.live_writes_allowed,
            "turn_interval_seconds": self.turn_interval_seconds,
            "test_only_stop_after_observed_turns": self.test_only_stop_after_observed_turns,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> OvernightFieldRunConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OvernightFieldRunConfig(**{**self.__dict__, "hash": compute_record_hash(body)})


def validate_field_run_config(
    config: OvernightFieldRunConfig,
    *,
    production_mode: bool = True,
) -> OvernightFieldRunConfig:
    import os

    policy = load_field_run_policy()
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
        errors.append(OvernightFieldRunVerdict.RED_FIXED_TURN_CAP.value)
    if production_mode and config.fixed_duration_cap is not None:
        errors.append(OvernightFieldRunVerdict.RED_FIXED_DURATION_CAP.value)
    if config.scheduler_allowed or config.cron_allowed:
        errors.append(OvernightFieldRunVerdict.RED_SCHEDULER.value)
    if config.daemon_allowed or config.service_allowed:
        errors.append(OvernightFieldRunVerdict.RED_SCHEDULER.value)
    if not config.manual_stop_required:
        errors.append(OvernightFieldRunVerdict.RED_STOP_UNAVAILABLE.value)
    if not config.panic_required:
        errors.append(OvernightFieldRunVerdict.RED_PANIC_UNAVAILABLE.value)
    if not config.foreground_required:
        errors.append(OvernightFieldRunVerdict.RED_BACKGROUND_SURVIVOR.value)
    if config.external_side_effects_allowed and not policy.get("external_side_effects_allowed", False) and not scoped_live:
        errors.append(OvernightFieldRunVerdict.RED_EXTERNAL_SIDE_EFFECT.value)
    if config.live_writes_allowed and not scoped_live:
        errors.append(OvernightFieldRunVerdict.RED_EXTERNAL_SIDE_EFFECT.value)

    if errors:
        raise FieldRunConfigError(errors[0])

    if not config.created_at:
        config = OvernightFieldRunConfig(**{**config.__dict__, "created_at": now_iso()})
    return config.with_hash()


def build_default_field_run_config(
    *,
    field_run_id: str,
    agent_id: str = "zero",
    mode: str = FieldRunMode.OPERATOR_FIELD_RUN.value,
    universe_ref: str = "",
    envelope_ref: str = "",
) -> OvernightFieldRunConfig:
    return validate_field_run_config(
        OvernightFieldRunConfig(
            field_run_id=field_run_id,
            agent_id=agent_id,
            mode=mode,
            objective_universe_ref=universe_ref,
            governed_work_envelope_ref=envelope_ref,
            created_at=now_iso(),
        )
    )


def build_smoke_config(*, field_run_id: str, observed_turns: int = 3) -> OvernightFieldRunConfig:
    return validate_field_run_config(
        OvernightFieldRunConfig(
            field_run_id=field_run_id,
            agent_id="zero",
            mode=FieldRunMode.INFRASTRUCTURE_SMOKE.value,
            test_only_stop_after_observed_turns=observed_turns,
            checkpoint_interval_turns=1,
            turn_interval_seconds=0.01,
            created_at=now_iso(),
        ),
        production_mode=False,
    )
