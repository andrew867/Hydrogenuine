"""Capability menu builder tests."""
from __future__ import annotations
import sys
from pathlib import Path
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_turn_engine.capability_builder import DISABLED_REASON_NO_PROVIDER, build_capability_menu_for_turn
from hg_runtime.agent_turn_engine.schema import PHASE_9_CONTENT_ACTIONS, PHASE_9_IMPLEMENTED_ACTIONS

def test_only_phase9_handlers_enabled():
    _, state = create_agent_state(agent_id="cap-a", runtime_mode="local_dev", run_id="cap-run")
    _, snap = build_observe_snapshot(agent_id="cap-a", turn_index=1, runtime_mode="local_dev",
        provider_reality_refs=["p1"], live_read_receipt_refs=["l1"])
    menu = build_capability_menu_for_turn(agent_state=state, observe_snapshot=snap,
        operator_presence="operator_present", provider_status="available", live_read_status="available")
    by_id = {a.action_id: a for a in menu.actions}
    for aid in PHASE_9_IMPLEMENTED_ACTIONS:
        assert by_id[aid].enabled, aid

def test_content_disabled_without_provider():
    _, state = create_agent_state(agent_id="cap-c", runtime_mode="local_dev", run_id="cap-run-3")
    _, snap = build_observe_snapshot(agent_id="cap-c", turn_index=1, runtime_mode="local_dev", provider_reality_refs=[], live_read_receipt_refs=[])
    menu = build_capability_menu_for_turn(agent_state=state, observe_snapshot=snap,
        operator_presence="operator_present", provider_status="unavailable", live_read_status="unavailable")
    by_id = {a.action_id: a for a in menu.actions}
    for aid in PHASE_9_CONTENT_ACTIONS:
        assert not by_id[aid].enabled
        assert by_id[aid].disabled_reason == DISABLED_REASON_NO_PROVIDER

def test_forbidden_not_enabled():
    _, state = create_agent_state(agent_id="cap-b", runtime_mode="local_dev", run_id="cap-run-2")
    _, snap = build_observe_snapshot(agent_id="cap-b", turn_index=1, runtime_mode="local_dev",
        provider_reality_refs=["p1"], live_read_receipt_refs=["l1"])
    menu = build_capability_menu_for_turn(agent_state=state, observe_snapshot=snap,
        operator_presence="operator_present", provider_status="available", live_read_status="available")
    ids = {a.action_id for a in menu.actions if a.enabled}
    assert "publish" not in ids and "send" not in ids
