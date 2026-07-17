"""Agent turn engine live provider dry mode tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnResult, AgentTurnVerdict, build_agent_turn_request

VALID = json.dumps({
    "observation_summary": "Quiet.",
    "reasoning_summary": "Rest.",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
})


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(tmp_path))
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_dry_turn_without_provider_yellow(tmp_path):
    req = build_agent_turn_request(agent_id="p15-a", run_id="p15-run", allow_provider=False)
    out = run_single_agent_turn(req, base=tmp_path)
    assert isinstance(out, AgentTurnResult)
    assert out.reasoning_failure_ref or out.verdict.value.startswith("YELLOW_")


def test_dry_turn_with_provider_double(tmp_path):
    req = build_agent_turn_request(agent_id="p15-b", run_id="p15-run-2", allow_provider=True)

    def _invoke(_p, _r):
        return VALID

    out = run_single_agent_turn(req, provider_invoke=_invoke, base=tmp_path)
    assert isinstance(out, AgentTurnResult)
    assert out.turn_receipt_ref
    assert out.broker_decision_ref
