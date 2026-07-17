"""Phase 5 no side effects / forbidden modules."""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

PHASE5_PKG = WORKSPACE / "hg_runtime" / "agent_zero_state"
FORBIDDEN = [
    WORKSPACE / "hg_runtime" / "bounded_soak" / "agent_turn.py",
    WORKSPACE / "hg_runtime" / "bounded_soak" / "agent_reasoning.py",
    WORKSPACE / "hg_runtime" / "bounded_soak" / "overnight_agent.py",
]


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_SOCIAL_LIVE_REPLY", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")


def test_no_reasoning_engine_file():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/agent_reasoning.py").is_file()


def test_no_autonomous_loop_file():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/overnight_agent.py").is_file()


def test_no_agent_turn_engine_file():
    assert not (WORKSPACE / "hg_runtime/bounded_soak/agent_turn.py").is_file()


def test_live_write_env_disabled():
    assert os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() != "true"
    assert os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower() != "true"


def test_no_empty_pass_stubs_in_phase5_package():
    offenders: list[str] = []
    for path in PHASE5_PKG.glob("*.py"):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    offenders.append(f"{path.name}:{node.name}")
    assert offenders == []


def test_forbidden_modules_absent():
    for path in FORBIDDEN:
        assert not path.is_file(), str(path)
