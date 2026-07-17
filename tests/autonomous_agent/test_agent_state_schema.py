"""AgentState schema tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.state import (  # noqa: E402
    AgentState,
    AgentStateVerdict,
    create_agent_state,
    validate_agent_state,
)


def test_valid_agent_state_hashes_deterministically():
    ts = "2026-06-17T00:00:00+00:00"
    s1 = AgentState(
        agent_id="agent-test-1",
        runtime_mode="local_dev",
        run_id="run-a",
        created_at=ts,
        updated_at=ts,
    ).with_hash()
    s2 = AgentState(
        agent_id="agent-test-1",
        runtime_mode="local_dev",
        run_id="run-a",
        created_at=ts,
        updated_at=ts,
    ).with_hash()
    assert s1.state_hash == s2.state_hash
    assert len(s1.state_hash) > 0
    verdict, _ = validate_agent_state(s1)
    assert verdict == AgentStateVerdict.GREEN_AGENT_STATE_VALID


def test_invalid_empty_agent_state_rejected():
    verdict, state = create_agent_state(agent_id="", runtime_mode="local_dev")
    assert verdict == AgentStateVerdict.RED_AGENT_STATE_EMPTY
    assert not state.state_hash or state.agent_id == ""


def test_fixture_runtime_state_rejected():
    state = create_agent_state(agent_id="a1", runtime_mode="fixture")[1]
    state = state.with_hash()
    verdict, _ = validate_agent_state(state)
    assert verdict == AgentStateVerdict.RED_AGENT_STATE_FIXTURE_RUNTIME
