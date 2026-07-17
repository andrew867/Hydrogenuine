"""ELS test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.emergence.config import ELSConfig
from hg_runtime.emergence.handler import Phase1ELSHandler


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-12T14:00:{counter['value']:02d}.000000Z"

    return tick


@pytest.fixture
def els_runtime_dir(tmp_path: Path) -> Path:
    return tmp_path / "runtime"


@pytest.fixture
def els_bus(els_runtime_dir: Path) -> EventBus:
    els_runtime_dir.mkdir(parents=True, exist_ok=True)
    return EventBus(els_runtime_dir, clock=_clock())


@pytest.fixture
def els_config() -> ELSConfig:
    return ELSConfig(
        enabled=True,
        agent_id="agent0",
        operator_id="operator1",
        profile="agent0_full",
        allow_degraded_memory=True,
        refuse_on_replay_mismatch=True,
    )


@pytest.fixture
def els_handler(els_config: ELSConfig, els_runtime_dir: Path) -> Phase1ELSHandler:
    return Phase1ELSHandler(config=els_config, runtime_dir=els_runtime_dir, clock=_clock())


def emit_drafts(bus: EventBus, drafts: list, source: str = "test:els") -> None:
    for d in drafts:
        bus.emit(
            d["type"],
            d["payload"],
            source=source,
            causal_parents=d.get("causal_parents", []),
        )
