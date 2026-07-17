"""YSR configuration — disabled by default."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.environ.get(name, default).strip()
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class YSRConfig:
    enabled: bool = False
    max_event_lag: int = 25
    max_scratch_age_seconds: int = 300
    clear_transient_buffers: bool = True
    escalate_to_crr_on_fail: bool = True
    agent_ids: tuple[str, ...] = ("agent0", "worker1")
    aep_suggest_severity: int = 5

    @classmethod
    def from_env(cls) -> YSRConfig:
        return cls(
            enabled=_truthy("HG_YSR_ENABLED", "0"),
            max_event_lag=_int("HG_YSR_MAX_EVENT_LAG", 25),
            max_scratch_age_seconds=_int("HG_YSR_MAX_SCRATCH_AGE_SECONDS", 300),
            clear_transient_buffers=_truthy("HG_YSR_CLEAR_TRANSIENT_BUFFERS", "1"),
            escalate_to_crr_on_fail=_truthy("HG_YSR_ESCALATE_TO_CRR_ON_FAIL", "1"),
            agent_ids=_csv("HG_YSR_AGENT_IDS", "agent0,worker1"),
            aep_suggest_severity=_int("HG_YSR_AEP_SUGGEST_SEVERITY", 5),
        )


def ysr_enabled() -> bool:
    return YSRConfig.from_env().enabled


__all__ = ["YSRConfig", "ysr_enabled"]
