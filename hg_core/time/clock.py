"""ClockService — UTC wall clock + monotonic durations (CT-11 TIM)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable


def format_rfc3339_z(dt: datetime) -> str:
    """Persisted timestamps: UTC RFC 3339 with Z and millisecond precision."""
    utc = dt.astimezone(timezone.utc)
    ms = utc.microsecond // 1000
    return f"{utc.strftime('%Y-%m-%dT%H:%M:%S')}.{ms:03d}Z"


def parse_rfc3339_z(value: str) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


@dataclass
class FakeClock:
    """Injectable UTC clock for deterministic tests."""

    _utc: datetime = field(
        default_factory=lambda: datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
    )
    _mono: float = 1000.0

    def now_utc(self) -> str:
        return format_rfc3339_z(self._utc)

    def now_datetime(self) -> datetime:
        return self._utc

    def monotonic(self) -> float:
        return self._mono

    def advance_ms(self, ms: int) -> None:
        self._utc += timedelta(milliseconds=ms)
        self._mono += ms / 1000.0

    def advance_seconds(self, seconds: float) -> None:
        self._utc += timedelta(seconds=seconds)
        self._mono += seconds

    def set_utc(self, value: str | datetime) -> None:
        if isinstance(value, str):
            parsed = parse_rfc3339_z(value)
            if parsed is None:
                raise ValueError(f"invalid RFC3339 timestamp: {value}")
            self._utc = parsed
            return
        self._utc = value.astimezone(timezone.utc)


class ClockService:
    def __init__(
        self,
        *,
        utc_source: Callable[[], datetime] | None = None,
        mono_source: Callable[[], float] | None = None,
    ) -> None:
        self._utc_source = utc_source or (lambda: datetime.now(timezone.utc))
        self._mono_source = mono_source or time.monotonic

    def now_utc(self) -> str:
        return format_rfc3339_z(self._utc_source())

    def now_datetime(self) -> datetime:
        return self._utc_source().astimezone(timezone.utc)

    def monotonic(self) -> float:
        return float(self._mono_source())


_default_clock: ClockService | FakeClock = ClockService()


def get_clock() -> ClockService | FakeClock:
    return _default_clock


def set_clock(clock: ClockService | FakeClock) -> None:
    global _default_clock
    _default_clock = clock


def reset_clock() -> None:
    set_clock(ClockService())


__all__ = [
    "ClockService",
    "FakeClock",
    "format_rfc3339_z",
    "get_clock",
    "parse_rfc3339_z",
    "reset_clock",
    "set_clock",
]
