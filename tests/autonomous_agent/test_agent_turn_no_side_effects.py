"""Phase 8 no side effects boundary tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")

def test_no_loop_scheduler_files():
    pkg = WORKSPACE / "hg_runtime/agent_turn_engine"
    for name in ("loop.py", "scheduler.py", "live_executor.py"):
        assert not (pkg / name).is_file()

def test_no_autonomous_loop():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/autonomous_loop.py").is_file()

def test_no_publish_send_in_engine():
    for name in ("engine.py", "context_builder.py", "capability_builder.py"):
        text = (WORKSPACE / "hg_runtime/agent_turn_engine" / name).read_text(encoding="utf-8")
        assert "publish(" not in text and "send(" not in text

def test_no_hardware_browser_calls():
    text = (WORKSPACE / "hg_runtime/agent_turn_engine/engine.py").read_text(encoding="utf-8")
    for token in ("hardware_actuate(", "browser_submit(", "reply_live(", "comment_live("):
        assert token not in text
