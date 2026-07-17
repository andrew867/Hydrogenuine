"""Phase 15 no external side effects tests."""
from __future__ import annotations

from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

FORBIDDEN_MODULES = [
    "hg_runtime/live_provider/live_publisher.py",
    "hg_runtime/live_provider/live_sender.py",
    "hg_runtime/live_autonomy/",
]


def test_no_live_write_modules():
    for rel in FORBIDDEN_MODULES:
        assert not (WORKSPACE / rel).exists()


def test_no_pass_stubs_in_live_provider():
    pkg = WORKSPACE / "hg_runtime/live_provider"
    for py in pkg.glob("*.py"):
        lines = py.read_text(encoding="utf-8").splitlines()
        assert not any(line.strip() == "pass" for line in lines), py.name


def test_policy_blocks_live_writes():
    import json

    pol = json.loads((WORKSPACE / "configs/agent_zero/live_provider_policy.json").read_text(encoding="utf-8"))
    assert pol["live_writes_allowed"] is False
    assert pol["external_side_effects_allowed"] is False
