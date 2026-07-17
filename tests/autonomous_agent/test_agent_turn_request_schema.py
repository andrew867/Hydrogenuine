"""Agent turn request schema tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_turn_engine.errors import AgentTurnValidationError
from hg_runtime.agent_turn_engine.schema import AgentTurnRequest, build_agent_turn_request, validate_agent_turn_request

def test_request_hash_deterministic():
    r = build_agent_turn_request(agent_id="a1", run_id="run-1")
    h1 = r.hash
    body = {k: v for k, v in r.to_payload().items() if k != "hash"}
    r2 = type(r)(**{**r.__dict__, **body}).with_hash()
    assert h1 == r2.hash

def test_external_side_effects_rejected():
    req = build_agent_turn_request(agent_id="a1", run_id="run-1")
    bad = AgentTurnRequest(**{**req.__dict__, "external_side_effects_allowed": True}).with_hash()
    with pytest.raises(AgentTurnValidationError):
        validate_agent_turn_request(bad)
