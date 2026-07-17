"""Phase 7 no execution boundary tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")

def test_no_agent_turn_engine():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/agent_turn.py").is_file()

def test_no_autonomous_loop():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/autonomous_loop.py").is_file()

def test_no_executor_or_live_dispatch():
    assert not (WORKSPACE / "hg_runtime/capability_broker/executor.py").is_file()
    assert not (WORKSPACE / "hg_runtime/capability_broker/live_dispatch.py").is_file()

def test_no_publish_send_in_broker():
    text = "\n".join(p.read_text(encoding="utf-8") for p in (WORKSPACE / "hg_runtime/capability_broker").glob("*.py"))
    assert "publish(" not in text and "send(" not in text

def test_no_pass_stubs():
    for py in (WORKSPACE / "hg_runtime/capability_broker").glob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            assert line.strip() != "pass"
