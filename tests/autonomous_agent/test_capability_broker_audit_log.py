"""Broker audit log tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu
from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent
from hg_runtime.capability_broker.audit_log import BrokerAuditLog
from hg_runtime.capability_broker.broker import evaluate_turn_intent, _build_request
from hg_runtime.capability_broker.decision_receipts import build_decision_receipt
from hg_runtime.capability_broker.errors import BrokerAuditError
from hg_runtime.capability_broker.policy import load_capability_broker_policy
from hg_runtime.capability_broker.schema import BrokerAuditRecord, BrokerVerdict

def test_audit_log_append_read(tmp_path):
    _, state = create_agent_state(agent_id="agent-b", runtime_mode="local_dev")
    _, snap = build_observe_snapshot(agent_id="agent-b", turn_index=1, runtime_mode="local_dev",
        provider_reality_refs=["prov-1"], live_read_receipt_refs=["live-1"])
    menu = build_capability_menu(runtime_mode="local_dev")
    _, intent = build_turn_intent(agent_id="agent-b", turn_index=1, chosen_action="rest_turn", menu=menu,
        observation_summary="rest", provider_receipt_ref="prov-1")
    log = BrokerAuditLog(tmp_path / "broker_audit.jsonl")
    evaluate_turn_intent(turn_intent=intent, agent_state=state, observe_snapshot=snap, capability_menu=menu, audit_log=log)
    assert len(log.read_all()) == 1
    log.verify_chain()

def test_decision_receipt_hash_deterministic():
    _, state = create_agent_state(agent_id="agent-b", runtime_mode="local_dev")
    _, snap = build_observe_snapshot(agent_id="agent-b", turn_index=1, runtime_mode="local_dev",
        provider_reality_refs=["prov-1"], live_read_receipt_refs=["live-1"])
    menu = build_capability_menu(runtime_mode="local_dev")
    _, intent = build_turn_intent(agent_id="agent-b", turn_index=1, chosen_action="rest_turn", menu=menu,
        observation_summary="rest", provider_receipt_ref="prov-1")
    request = _build_request(turn_intent=intent, agent_state=state, observe_snapshot=snap, capability_menu=menu)
    decision = evaluate_turn_intent(turn_intent=intent, agent_state=state, observe_snapshot=snap, capability_menu=menu)
    ph = load_capability_broker_policy().policy_hash()
    assert build_decision_receipt(request=request, decision=decision, policy_hash=ph).hash == build_decision_receipt(request=request, decision=decision, policy_hash=ph).hash

def test_audit_log_rejects_secret(tmp_path):
    log = BrokerAuditLog(tmp_path / "broker_audit.jsonl")
    bad = BrokerAuditRecord(record_id="a1", decision_id="d1", request_id="r1", agent_id="agent-b", turn_index=1,
        chosen_action="rest_turn", verdict=BrokerVerdict.YELLOW_BROKER_REST.value, status="rest", admitted=True,
        refused=False, refusal_reasons=["Bearer sk-secret"], created_at="2026-06-17T00:00:00+00:00").with_hash()
    with pytest.raises(BrokerAuditError):
        log.append(bad)

def test_audit_log_rejects_hidden_cot(tmp_path):
    log = BrokerAuditLog(tmp_path / "broker_audit.jsonl")
    bad = BrokerAuditRecord(record_id="a2", decision_id="d1", request_id="r1", agent_id="agent-b", turn_index=1,
        chosen_action="rest_turn", verdict=BrokerVerdict.YELLOW_BROKER_REST.value, status="rest", admitted=True,
        refused=False, refusal_reasons=["scratchpad leak"], created_at="2026-06-17T00:00:00+00:00").with_hash()
    with pytest.raises(BrokerAuditError):
        log.append(bad)
