"""Phase 9 no external side effects."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")

def test_no_publisher_sender_modules():
    pkg = WORKSPACE / "hg_runtime/output_artifacts"
    for name in ("publisher.py", "sender.py", "live_reply.py", "live_comment.py"):
        assert not (pkg / name).is_file()

def test_no_autonomous_loop():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/autonomous_loop.py").is_file()

def test_no_pass_stubs():
    for py in (WORKSPACE / "hg_runtime/output_artifacts").glob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            assert line.strip() != "pass"

def test_no_publish_in_output_artifacts():
    text = "\n".join(p.read_text(encoding="utf-8") for p in (WORKSPACE / "hg_runtime/output_artifacts").glob("*.py"))
    assert "publish(" not in text and "send(" not in text
