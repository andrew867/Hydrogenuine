"""Phase 11 no external side effects."""
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


def test_no_autonomous_loop_files():
    for name in ("autonomous_loop.py", "overnight_agent.py", "unbounded_loop.py"):
        assert not (WORKSPACE / "hg_runtime/bounded_soak" / name).is_file()
        assert not (WORKSPACE / "hg_runtime/supervised_rehearsal" / name).is_file()


def test_no_live_publisher_sender():
    pkg = WORKSPACE / "hg_runtime/supervised_rehearsal"
    for name in ("live_publisher.py", "live_sender.py"):
        assert not (pkg / name).is_file()


def test_no_pass_stubs():
    for py in (WORKSPACE / "hg_runtime/supervised_rehearsal").glob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            assert line.strip() != "pass"


def test_no_publish_send_in_package():
    text = "\n".join(p.read_text(encoding="utf-8") for p in (WORKSPACE / "hg_runtime/supervised_rehearsal").glob("*.py"))
    assert "publish(" not in text
    assert "send(" not in text
