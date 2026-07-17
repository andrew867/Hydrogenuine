"""Phase 6 no execution boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_SOCIAL_LIVE_REPLY", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_LIVE_BROWSER_ENABLED", "false")
    monkeypatch.setenv("HG_EXTERNAL_SEND_ENABLED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")


def test_no_agent_turn_engine_file():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/agent_turn.py").is_file()
    assert not (WORKSPACE / "hg_runtime/bounded_soak/agent_turn_engine.py").is_file()


def test_no_autonomous_loop_file():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/overnight_agent.py").is_file()
    assert not (WORKSPACE / "hg_runtime/bounded_soak/autonomous_loop.py").is_file()


def test_no_soak_started():
    import os
    assert os.environ.get("HG_COGNITIVE_SOAK_ACTIVE", "0") == "0"


def test_no_live_writes_enabled():
    import os
    assert os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() != "true"
    assert os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower() != "true"


def test_no_publish_send_reply_browser_in_reasoning_package():
    pkg = WORKSPACE / "hg_runtime/agent_zero_reasoning"
    text = "\n".join(p.read_text(encoding="utf-8") for p in pkg.glob("*.py"))
    for forbidden in ("publish(", "send(", "reply_live", "comment_live", "browser_submit"):
        assert forbidden not in text


def test_no_empty_pass_stubs_in_reasoning_package():
    pkg = WORKSPACE / "hg_runtime/agent_zero_reasoning"
    for py in pkg.glob("*.py"):
        lines = py.read_text(encoding="utf-8").splitlines()
        for line in lines:
            assert line.strip() != "pass"


def test_reasoning_engine_has_no_execution_imports():
    source = (WORKSPACE / "hg_runtime/agent_zero_reasoning/reasoning_engine.py").read_text(encoding="utf-8")
    assert "capability_broker" not in source
    assert "bounded_soak/agent_turn" not in source
