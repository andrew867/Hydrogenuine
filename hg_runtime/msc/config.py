"""MSC configuration from environment — disabled by default."""

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
class MSCConfig:
    enabled: bool = False
    mode: str = "deterministic"
    max_events: int = 50
    max_age_seconds: int = 300
    agent_ids: tuple[str, ...] = ("agent0", "worker1")
    allow_model_summary: bool = False
    cycle_every_ticks: int = 0  # 0 = only on explicit request / aep suggest

    @classmethod
    def from_env(cls) -> MSCConfig:
        return cls(
            enabled=_truthy("HG_MSC_ENABLED", "0"),
            mode=os.environ.get("HG_MSC_MODE", "deterministic").strip().lower(),
            max_events=_int("HG_MSC_MAX_EVENTS", 50),
            max_age_seconds=_int("HG_MSC_MAX_AGE_SECONDS", 300),
            agent_ids=_csv("HG_MSC_AGENT_IDS", "agent0,worker1"),
            allow_model_summary=_truthy("HG_MSC_ALLOW_MODEL_SUMMARY", "0"),
            cycle_every_ticks=_int("HG_MSC_CYCLE_EVERY_TICKS", 0),
        )


def msc_enabled() -> bool:
    return MSCConfig.from_env().enabled


__all__ = ["MSCConfig", "msc_enabled"]
