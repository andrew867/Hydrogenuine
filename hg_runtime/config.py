"""RTC runtime configuration — Phase 1 persistent loop controller."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from hg_runtime.handlers.registry import HandlerRegistry
from hg_runtime.loop import DEFAULT_IDLE_BLOCK_S, DEFAULT_SNAPSHOT_EVERY_TICKS, DEFAULT_TICK_BUDGET_S


@dataclass
class RuntimeConfig:
    """Configuration for a bounded or daemon-like RTC runtime loop."""

    runtime_dir: Path
    tick_interval_s: float = 0.0
    max_ticks: Optional[int] = None
    run_until_stopped: bool = False
    idle_block_s: float = DEFAULT_IDLE_BLOCK_S
    tick_budget_s: float = DEFAULT_TICK_BUDGET_S
    snapshot_every_ticks: int = DEFAULT_SNAPSHOT_EVERY_TICKS
    panic_flag_path: Optional[Path] = None
    handlers: HandlerRegistry = field(default_factory=HandlerRegistry.build_from_env)
    governance_trace: Any = None
    require_enabled: bool = True
    phase1_lifecycle: bool = True

    def __post_init__(self) -> None:
        self.runtime_dir = Path(self.runtime_dir)
        if self.panic_flag_path is not None:
            self.panic_flag_path = Path(self.panic_flag_path)
        if self.max_ticks is not None and self.max_ticks < 1:
            raise ValueError("max_ticks must be >= 1 when set")
        if self.run_until_stopped and self.max_ticks is not None:
            raise ValueError("set either max_ticks or run_until_stopped, not both")

    @property
    def resolved_panic_path(self) -> Path:
        return self.panic_flag_path or (self.runtime_dir / "PANIC")

    @classmethod
    def from_env(cls, runtime_dir: Optional[Path] = None) -> RuntimeConfig:
        """Load common settings from environment variables."""
        root = Path(runtime_dir or os.environ.get("HG_RTC_RUNTIME_DIR", "memory/runtime"))
        max_ticks_raw = os.environ.get("HG_RTC_MAX_TICKS", "").strip()
        max_ticks = int(max_ticks_raw) if max_ticks_raw else None
        run_until = os.environ.get("HG_RTC_RUN_UNTIL_STOPPED", "0").strip() == "1"
        return cls(
            runtime_dir=root,
            tick_interval_s=float(os.environ.get("HG_RTC_TICK_INTERVAL_S", "0")),
            max_ticks=max_ticks,
            run_until_stopped=run_until,
            idle_block_s=float(os.environ.get("HG_RTC_IDLE_BLOCK_S", str(DEFAULT_IDLE_BLOCK_S))),
            require_enabled=os.environ.get("HG_RTC_ENABLED", "0").strip() == "1",
            handlers=HandlerRegistry.build_from_env(runtime_dir=root),
        )


__all__ = ["RuntimeConfig"]
