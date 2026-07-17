"""ELS handler — wake lifecycle before work admission."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

from hg_runtime.emergence.config import ELSConfig
from hg_runtime.emergence.lifecycle import run_wake_cycle
from hg_runtime.emergence.report import build_wake_report
from hg_runtime.emergence.types import WakeRequest, WakeResult


class StubELSHandler:
    """No-op ELS handler — work admission open when disabled."""

    handler_id = "rtc.stub.els"

    def __init__(self) -> None:
        self._last_result: WakeResult | None = None

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        del bus, state

    def run_wake(
        self,
        *,
        panic_active: bool = False,
        lockdown_active: bool = False,
    ) -> List[Dict[str, Any]]:
        del panic_active, lockdown_active
        return []

    @property
    def work_admission_open(self) -> bool:
        return True

    @property
    def last_result(self) -> WakeResult | None:
        return self._last_result

    @property
    def last_report(self) -> dict[str, Any] | None:
        if self._last_result is None:
            return None
        return build_wake_report(self._last_result)


class Phase1ELSHandler:
    """Bounded emergence lifecycle wake sequence."""

    handler_id = "rtc.els.phase1"

    def __init__(
        self,
        *,
        config: ELSConfig | None = None,
        runtime_dir: Path | None = None,
        clock: Any = None,
    ) -> None:
        self._config = config or ELSConfig.from_env()
        self._runtime_dir = runtime_dir
        self._clock = clock
        self._bus: Any = None
        self._state: Mapping[str, Any] | None = None
        self._last_result: WakeResult | None = None

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        self._bus = bus
        self._state = state
        if self._runtime_dir is None and hasattr(bus, "runtime_dir"):
            self._runtime_dir = Path(bus.runtime_dir)

    def _now(self) -> str:
        if callable(self._clock):
            return str(self._clock())
        if self._bus is not None and hasattr(self._bus, "clock"):
            return str(self._bus.clock())
        return "1970-01-01T00:00:00.000000Z"

    def run_wake(
        self,
        *,
        panic_active: bool = False,
        lockdown_active: bool = False,
        memory_available: bool = True,
        stale_scratch: bool = False,
        replay_force_fail: bool = False,
        profile: str | None = None,
    ) -> List[Dict[str, Any]]:
        if not self._config.enabled or self._bus is None or self._runtime_dir is None:
            return []
        request = WakeRequest(
            agent_id=self._config.agent_id,
            profile=profile or self._config.profile,
            operator_id=self._config.operator_id,
            reason_code="handler_wake",
        )
        drafts, result = run_wake_cycle(
            config=self._config,
            request=request,
            bus=self._bus,
            runtime_dir=self._runtime_dir,
            clock_now=self._now(),
            panic_active=panic_active,
            lockdown_active=lockdown_active,
            memory_available=memory_available,
            stale_scratch=stale_scratch,
            replay_force_fail=replay_force_fail,
        )
        self._last_result = result
        return drafts

    @property
    def work_admission_open(self) -> bool:
        if not self._config.enabled:
            return True
        if self._last_result is None:
            return False
        return self._last_result.work_admission_open

    @property
    def last_result(self) -> WakeResult | None:
        return self._last_result

    @property
    def last_report(self) -> dict[str, Any] | None:
        if self._last_result is None:
            return None
        return build_wake_report(self._last_result)


__all__ = ["Phase1ELSHandler", "StubELSHandler"]
