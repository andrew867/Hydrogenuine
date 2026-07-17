"""YSR test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubRecoveryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.msc.handler import StubMSCHandler
from hg_runtime.yawn.config import YSRConfig
from hg_runtime.yawn.handler import Phase1YSRHandler, StubYSRHandler
from hg_runtime.yawn.scratch import seed_transient_scratch


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T15:00:{counter['value']:02d}.000000Z"

    return tick


@pytest.fixture
def ysr_runtime_dir(tmp_path: Path) -> Path:
    return tmp_path / "runtime"


@pytest.fixture
def ysr_bus(ysr_runtime_dir: Path) -> EventBus:
    ysr_runtime_dir.mkdir(parents=True, exist_ok=True)
    return EventBus(ysr_runtime_dir, clock=_clock())


@pytest.fixture
def ysr_config() -> YSRConfig:
    return YSRConfig(
        enabled=True,
        max_event_lag=5,
        max_scratch_age_seconds=60,
        clear_transient_buffers=True,
        escalate_to_crr_on_fail=True,
        agent_ids=("agent0",),
        aep_suggest_severity=5,
    )


@pytest.fixture
def ysr_handler(ysr_config: YSRConfig, ysr_runtime_dir: Path) -> Phase1YSRHandler:
    return Phase1YSRHandler(
        config=ysr_config,
        runtime_dir=ysr_runtime_dir,
        clock=_clock(),
        requested=True,
        agent_ids=("agent0",),
    )


@pytest.fixture
def ysr_loop(ysr_bus: EventBus, ysr_runtime_dir: Path, ysr_handler: Phase1YSRHandler) -> RuntimeLoop:
    return RuntimeLoop(
        ysr_bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        yawn=ysr_handler,
        meditation=StubMSCHandler(),
        runtime_dir=ysr_runtime_dir,
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )


@pytest.fixture
def stale_scratch(ysr_runtime_dir: Path) -> None:
    seed_transient_scratch(ysr_runtime_dir, "agent0", event_head_seq=1)
