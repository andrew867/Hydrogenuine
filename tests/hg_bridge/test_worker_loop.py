"""Tests for Phase 5: worker loop integration (bridge scheduler + meditation worker in one process)."""

import json
from pathlib import Path
import pytest

from hg_bridge.config import BridgeConfig, load_bridge_config


def test_load_bridge_config_defaults_when_no_file():
    """load_bridge_config returns default BridgeConfig when memory/automation/bridge_config.json is missing."""
    cfg = load_bridge_config(Path("/nonexistent"))
    assert cfg.trailing_window_s == 900.0
    assert cfg.idle_min_s == 30.0
    assert cfg.meditate_dedup_window_s == 60.0


def test_load_bridge_config_from_file(tmp_path):
    """load_bridge_config loads from memory/automation/bridge_config.json when present."""
    automation = tmp_path / "memory" / "automation"
    automation.mkdir(parents=True)
    config_path = automation / "bridge_config.json"
    config_path.write_text(
        json.dumps({
            "trailing_window_s": 600.0,
            "idle_min_s": 45.0,
            "meditate_dedup_window_s": 120.0,
        }),
        encoding="utf-8",
    )
    cfg = load_bridge_config(tmp_path)
    assert cfg.trailing_window_s == 600.0
    assert cfg.idle_min_s == 45.0
    assert cfg.meditate_dedup_window_s == 120.0


def test_load_bridge_config_fallback_env(monkeypatch):
    """load_bridge_config uses HG_BRIDGE_* env when no config file."""
    monkeypatch.setenv("HG_BRIDGE_TRAILING_WINDOW_S", "300")
    monkeypatch.setenv("HG_BRIDGE_IDLE_MIN_S", "10")
    monkeypatch.setenv("HG_BRIDGE_MEDITATE_DEDUP_WINDOW_S", "90")
    cfg = load_bridge_config(Path("/nonexistent"))
    assert cfg.trailing_window_s == 300.0
    assert cfg.idle_min_s == 10.0
    assert cfg.meditate_dedup_window_s == 90.0


def test_worker_loop_includes_bridge_and_meditation():
    """Worker main loop runs scheduler, bridge_scheduler, meditation_worker, then reflection_worker (structure check)."""
    import hg_realtime.worker as worker_mod
    source = Path(worker_mod.__file__).read_text(encoding="utf-8")
    assert "scheduler.tick_once()" in source
    assert "bridge_scheduler.tick_once()" in source
    assert "meditation_worker.tick_once()" in source
    assert "reflection_worker.tick_once()" in source
    assert "load_bridge_config" in source
    assert "CognitionBridgeScheduler" in source
    assert "MeditationWorker" in source
    assert "RunDirTraceStore" in source
    assert "ContextualSteeringSink" in source
    assert "ReflectionWorker" in source
