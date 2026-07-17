"""Persistent RTC loop controller — bounded and run-until-stopped modes."""

from __future__ import annotations

import time
from typing import Callable, Optional

from hg_runtime import world_state as ws
from hg_runtime.bus import BusWriteError, EventBus
from hg_runtime.config import RuntimeConfig
from hg_runtime.contract import validate_drafts
from hg_runtime.emergence.config import ELSConfig
from hg_runtime.emergence.handler import Phase1ELSHandler, StubELSHandler
from hg_runtime.loop import PanicFlag, RuntimeLoop


class PersistentLoopController:
    """
    Phase 1 controller over ``RuntimeLoop``.

    Supports bounded tick runs for tests and daemon-like ``run_until_stopped``
    without changing tick order or handler contracts.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._monotonic = monotonic
        self.runtime_dir = config.runtime_dir
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.bus = EventBus(self.runtime_dir)
        self.panic = PanicFlag(config.resolved_panic_path)
        self.loop: RuntimeLoop = config.handlers.build_loop(
            self.bus,
            runtime_dir=self.runtime_dir,
            panic=self.panic,
            governance_trace=config.governance_trace,
            idle_block_s=config.idle_block_s,
            tick_budget_s=config.tick_budget_s,
            snapshot_every_ticks=config.snapshot_every_ticks,
            require_enabled=config.require_enabled,
            phase1_lifecycle=config.phase1_lifecycle,
        )
        els_cfg = ELSConfig.from_env()
        if els_cfg.enabled:
            self.emergence = Phase1ELSHandler(config=els_cfg, runtime_dir=self.runtime_dir)
        else:
            self.emergence = StubELSHandler()
        self.emergence.bind_runtime(self.bus, self.loop.state)
        self._wake_completed = False

    def request_stop(self, reason: str = "requested") -> None:
        self.loop.alive = False
        if self.loop._started:
            self.loop.stop(reason=reason)

    def run_bounded(self, max_ticks: Optional[int] = None) -> int:
        """Run until ``max_ticks`` productive ticks complete, then stop cleanly."""
        limit = max_ticks if max_ticks is not None else self.config.max_ticks
        if limit is None or limit < 1:
            raise ValueError("bounded run requires max_ticks >= 1")
        return self._drive_loop(tick_limit=limit)

    def run_until_stopped(self) -> int:
        """Daemon-like loop until ``request_stop`` or ``alive`` is cleared."""
        if not self.config.run_until_stopped and self.config.max_ticks is None:
            self.config.run_until_stopped = True
        return self._drive_loop(tick_limit=None)

    def run_once(self, poll_timeout: Optional[float] = None) -> str:
        return self.loop.run_once(poll_timeout=poll_timeout)

    def run_wake(self) -> bool:
        """Run ELS wake sequence; return whether work admission is open."""
        if self._wake_completed:
            return self.emergence.work_admission_open
        panic_active = self.panic.active()
        drafts = validate_drafts(
            self.emergence.run_wake(panic_active=panic_active),
            self.emergence.handler_id,
        )
        for d in drafts:
            event = self.bus.emit(
                d["type"],
                d["payload"],
                source=self.emergence.handler_id,
                causal_parents=d.get("causal_parents", []),
            )
            self.loop.state = ws.apply(self.loop.state, event)
        self._wake_completed = True
        return self.emergence.work_admission_open

    def _drive_loop(self, *, tick_limit: Optional[int]) -> int:
        if not self.run_wake():
            self.loop._write_status("wake_refused")
            return 1
        self.loop.start()
        completed = 0
        try:
            while self.loop.alive:
                if tick_limit is not None and completed >= tick_limit:
                    break
                outcome = self.loop.run_once()
                if outcome in ("tick", "recovery"):
                    completed += 1
                elif outcome == "panic" and self.config.tick_interval_s > 0:
                    time.sleep(min(self.config.tick_interval_s, 1.0))
                elif outcome == "idle" and self.config.tick_interval_s > 0:
                    time.sleep(self.config.tick_interval_s)
        except BusWriteError:
            self.loop._write_status("fatal_bus_write")
            return 1
        except KeyboardInterrupt:
            self.loop.stop(reason="signal")
            return 0
        reason = "bounded_complete" if tick_limit is not None else "alive=False"
        self.loop.stop(reason=reason)
        return 0


__all__ = ["PersistentLoopController"]
