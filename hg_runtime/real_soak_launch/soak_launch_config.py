"""Real soak launch configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.real_soak_launch.schema import now_iso, soak_dir


@dataclass
class RealSoakLaunchConfig:
    soak_id: str
    agent_id: str
    field_run_config_ref: str = ""
    hands_off_session_ref: str = ""
    governed_work_envelope_ref: str = ""
    moltbook_envelope_ref: str = ""
    live_posts_default_allowed: bool = False
    operator_prearm_required: bool = True
    foreground_required: bool = True
    manual_stop_required: bool = True
    panic_required: bool = True
    scheduler_allowed: bool = False
    daemon_allowed: bool = False
    service_allowed: bool = False
    cron_allowed: bool = False
    created_at: str = ""
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "soak_id": self.soak_id,
            "agent_id": self.agent_id,
            "field_run_config_ref": self.field_run_config_ref,
            "hands_off_session_ref": self.hands_off_session_ref,
            "governed_work_envelope_ref": self.governed_work_envelope_ref,
            "moltbook_envelope_ref": self.moltbook_envelope_ref,
            "live_posts_default_allowed": self.live_posts_default_allowed,
            "operator_prearm_required": self.operator_prearm_required,
            "foreground_required": self.foreground_required,
            "manual_stop_required": self.manual_stop_required,
            "panic_required": self.panic_required,
            "scheduler_allowed": self.scheduler_allowed,
            "daemon_allowed": self.daemon_allowed,
            "service_allowed": self.service_allowed,
            "cron_allowed": self.cron_allowed,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> RealSoakLaunchConfig:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return RealSoakLaunchConfig(**{**self.__dict__, "hash": compute_record_hash(body)})


def build_launch_config(*, soak_id: str, agent_id: str = "zero") -> RealSoakLaunchConfig:
    return RealSoakLaunchConfig(
        soak_id=soak_id,
        agent_id=agent_id,
        field_run_config_ref=str(soak_dir(soak_id) / "field_run_config.json"),
        hands_off_session_ref=soak_id,
        live_posts_default_allowed=False,
        created_at=now_iso(),
    ).with_hash()
