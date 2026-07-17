"""ELS configuration from environment — disabled by default."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class ELSConfig:
    enabled: bool = False
    agent_id: str = "agent0"
    operator_id: str | None = None
    profile: str = "agent0_full"
    require_resync: bool = False
    allow_quiet_settling: bool = False
    allow_degraded_memory: bool = True
    refuse_on_replay_mismatch: bool = True
    ysr_on_stale_scratch: bool = True
    msc_on_wake: bool = False

    @classmethod
    def from_env(cls) -> ELSConfig:
        return cls(
            enabled=_truthy("HG_ELS_ENABLED", "0"),
            agent_id=os.environ.get("HG_ELS_AGENT_ID", "agent0").strip() or "agent0",
            operator_id=os.environ.get("HG_ELS_OPERATOR_ID", "").strip() or None,
            profile=os.environ.get("HG_ELS_PROFILE", "agent0_full").strip().lower(),
            require_resync=_truthy("HG_ELS_REQUIRE_RESYNC", "0"),
            allow_quiet_settling=_truthy("HG_ELS_ALLOW_QUIET_SETTLING", "0"),
            allow_degraded_memory=_truthy("HG_ELS_ALLOW_DEGRADED_MEMORY", "1"),
            refuse_on_replay_mismatch=_truthy("HG_ELS_REFUSE_REPLAY_MISMATCH", "1"),
            ysr_on_stale_scratch=_truthy("HG_ELS_YSR_ON_STALE", "1"),
            msc_on_wake=_truthy("HG_ELS_MSC_ON_WAKE", "0"),
        )


def els_enabled() -> bool:
    return ELSConfig.from_env().enabled


__all__ = ["ELSConfig", "els_enabled"]
