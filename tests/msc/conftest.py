"""MSC test fixtures."""

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
from hg_runtime.msc.config import MSCConfig
from hg_runtime.msc.handler import Phase1MSCHandler, StubMSCHandler
from hg_runtime.msc.registry import SubAgentRegistry
from hg_runtime.msc.types import SubAgentIdentity


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T12:00:{counter['value']:02d}.000000Z"

    return tick


@pytest.fixture
def msc_runtime_dir(tmp_path: Path) -> Path:
    return tmp_path / "runtime"


@pytest.fixture
def msc_bus(msc_runtime_dir: Path) -> EventBus:
    msc_runtime_dir.mkdir(parents=True, exist_ok=True)
    return EventBus(msc_runtime_dir, clock=_clock())


@pytest.fixture
def msc_config() -> MSCConfig:
    return MSCConfig(
        enabled=True,
        mode="deterministic",
        max_events=50,
        max_age_seconds=300,
        agent_ids=("agent0",),
        allow_model_summary=False,
        cycle_every_ticks=0,
    )


@pytest.fixture
def msc_handler(msc_config: MSCConfig, msc_runtime_dir: Path) -> Phase1MSCHandler:
    registry = SubAgentRegistry(
        {
            "agent0": SubAgentIdentity(
                agent_id="agent0",
                meditation_enabled=True,
                max_window_events=10,
            )
        }
    )
    return Phase1MSCHandler(
        config=msc_config,
        registry=registry,
        runtime_dir=msc_runtime_dir,
        clock=_clock(),
        requested=True,
    )


@pytest.fixture
def msc_loop(msc_bus: EventBus, msc_runtime_dir: Path, msc_handler: Phase1MSCHandler) -> RuntimeLoop:
    return RuntimeLoop(
        msc_bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        meditation=msc_handler,
        runtime_dir=msc_runtime_dir,
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )


@pytest.fixture
def stub_msc_loop(msc_bus: EventBus, msc_runtime_dir: Path) -> RuntimeLoop:
    return RuntimeLoop(
        msc_bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        meditation=StubMSCHandler(),
        runtime_dir=msc_runtime_dir,
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
