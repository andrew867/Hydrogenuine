"""Shared lifecycle tests on demo_phase0 and phase1_integrated paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.config import RuntimeConfig
from hg_runtime.controller import PersistentLoopController
from hg_runtime.demo import build_loop
from hg_runtime.handlers import HandlerRegistry
from hg_runtime.replay import replay


def _clock():
    n = {"v": 0}

    def tick() -> str:
        n["v"] += 1
        return f"2026-06-12T16:00:{n['v']:02d}.000000Z"

    return tick


def _run_demo_path(runtime_dir: Path) -> list[str]:
    loop = build_loop(runtime_dir, require_enabled=False, phase1_lifecycle=True)
    loop.start()
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "parity", "role": "user", "content": "demo path tick"},
        source="parity.test",
    )
    loop.run_once(poll_timeout=0.0)
    loop.stop(reason="test")
    return [e["type"] for e in loop.bus.read_all()]


def _run_integrated_path(runtime_dir: Path) -> list[str]:
    config = RuntimeConfig(runtime_dir=runtime_dir, require_enabled=False, phase1_lifecycle=True, idle_block_s=0.0)
    controller = PersistentLoopController(config)
    controller.loop.start()
    controller.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "parity", "role": "user", "content": "integrated path tick"},
        source="parity.test",
    )
    controller.run_once(poll_timeout=0.0)
    controller.loop.stop(reason="test")
    return [e["type"] for e in controller.bus.read_all()]


@pytest.mark.parametrize("runner,path_id", [(_run_demo_path, "demo_phase0"), (_run_integrated_path, "phase1_integrated")])
def test_shared_lifecycle_tick(tmp_path, runner, path_id):
    runtime_dir = tmp_path / path_id
    runtime_dir.mkdir()
    types = runner(runtime_dir)
    assert "CHAT_MESSAGE" in types
    assert any(t in types for t in ("TICK_COMPLETED", "RUNTIME_TICK_COMPLETED"))
    assert replay(runtime_dir).ok is True


def test_integrated_emits_hal_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_HAL_ENABLED", "1")
    monkeypatch.setenv("HG_GPP_PERMIT_BIND", "1")
    runtime_dir = tmp_path / "integrated_hal"
    types = _run_integrated_path(runtime_dir)
    assert any(t.startswith("HAL_") or t.startswith("SOAR_") for t in types)


def test_demo_path_does_not_emit_hal(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_HAL_ENABLED", "1")
    runtime_dir = tmp_path / "demo_no_hal"
    types = _run_demo_path(runtime_dir)
    assert not any(t.startswith("HAL_") for t in types)
