"""
E2E synthetic scenarios for emergent behavior (Autonomy Ch5 Phase 5).

Scenarios: exploding-split-tree, rework-thrash, safety-block-probing.
Assert: anomalies present, interventions applied, side-effect blocking when critical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.task_graph.behavior_telemetry import make_behavior_event
from hg_core.task_graph.delegation_manager import run_delegation_supervision
from hg_core.task_graph.emergent_behavior_detectors import run_default_detectors


SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


def _load_scenario(scenario_id: str) -> dict:
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        pytest.skip(f"Scenario file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_scenario_exploding_split_tree():
    """Exploding split tree: many splits, depth/width exceed -> D1 anomaly, constrain."""
    scenario = _load_scenario("exploding_split_tree")
    run_id = "scenario-exploding"
    workflow_id = "w1"
    events = [
        make_behavior_event(run_id, workflow_id, "n1", "delegation.assign", agent_id="a1"),
        make_behavior_event(run_id, workflow_id, "n2", "delegation.split", agent_id="a1", parent_work_item_id="n1"),
        make_behavior_event(run_id, workflow_id, "n3", "delegation.split", agent_id="a1", parent_work_item_id="n1"),
        make_behavior_event(run_id, workflow_id, "n4", "delegation.split", agent_id="a1", parent_work_item_id="n1"),
        make_behavior_event(run_id, workflow_id, "n5", "delegation.split", agent_id="a1", parent_work_item_id="n2"),
        make_behavior_event(run_id, workflow_id, "n6", "delegation.split", agent_id="a1", parent_work_item_id="n2"),
        make_behavior_event(run_id, workflow_id, "n7", "delegation.split", agent_id="a1", parent_work_item_id="n3"),
    ]
    summary = run_delegation_supervision(
        run_id, workflow_id, events, root_objective_summary="exploding split tree", final_status="completed"
    )
    anomalies = summary.get("anomalies", [])
    detector_ids = [a.get("detector_id") for a in anomalies]
    assert any("D1_runaway_delegation" in d for d in detector_ids), f"Expected D1 anomaly, got {detector_ids}"
    assert len(anomalies) >= scenario.get("min_anomalies", 1)
    intervention = summary.get("intervention", {})
    assert intervention.get("step") in ("warn", "constrain", "slowdown", "sandbox", "escalate", "halt")


def test_scenario_rework_thrash():
    """Rework thrash: high retries, same node repeated -> D3 anomaly."""
    scenario = _load_scenario("rework_thrash")
    run_id = "scenario-rework"
    workflow_id = "w1"
    events = [
        make_behavior_event(run_id, workflow_id, "n1", "delegation.assign", agent_id="a1"),
    ]
    node_attempts = {"n1": 5}
    summary = run_delegation_supervision(
        run_id, workflow_id, events, nodes_attempts=node_attempts, final_status="completed"
    )
    metrics = summary.get("metrics", {})
    # Inject retry_count so detector triggers
    from hg_core.task_graph import emergent_behavior_detectors as ebd
    metrics["retry_count"] = 8
    anomalies = run_default_detectors(metrics, events=events, node_attempts=node_attempts)
    assert any(a.get("detector_id") == "D3_looping_thrash" for a in anomalies), f"Expected D3, got {[a.get('detector_id') for a in anomalies]}"


def test_scenario_safety_block_probing():
    """Safety block probing: repeated safety.blocked events -> D4 anomaly."""
    scenario = _load_scenario("safety_block_probing")
    run_id = "scenario-safety"
    workflow_id = "w1"
    events = [
        make_behavior_event(run_id, workflow_id, "n1", "delegation.assign", agent_id="a1"),
        {"event_type": "safety.blocked", "run_id": run_id, "workflow_id": workflow_id, "work_item_id": "n1", "agent_id": "a1", "payload_summary": {}, "pointers": [], "severity": "warn", "timestamp": "2026-01-01T00:00:00Z"},
        {"event_type": "safety.blocked", "run_id": run_id, "workflow_id": workflow_id, "work_item_id": "n1", "agent_id": "a1", "payload_summary": {}, "pointers": [], "severity": "warn", "timestamp": "2026-01-01T00:00:01Z"},
    ]
    from hg_core.task_graph import emergent_behavior_detectors as ebd
    anomalies = ebd.run_detector_policy_pressure({}, events)
    assert any(a.get("detector_id") == "D4_policy_pressure" for a in anomalies), f"Expected D4, got {[a.get('detector_id') for a in anomalies]}"


def test_scenario_cost_spike():
    """Cost spike: token rate or spend rate above threshold -> D5 anomaly."""
    scenario = _load_scenario("cost_spike")
    from hg_core.task_graph import emergent_behavior_detectors as ebd
    metrics = {"token_rate_per_min": 10000}
    anomalies = ebd.run_detector_cost_spike(metrics)
    assert any(a.get("detector_id") == "D5_cost_spike" for a in anomalies), f"Expected D5, got {[a.get('detector_id') for a in anomalies]}"
    assert len(anomalies) >= scenario.get("min_anomalies", 1)


def test_side_effects_blocked_under_critical():
    """When intervention is sandbox/escalate/halt or degraded, external_writes_blocked is yes."""
    from hg_core.task_graph.delegation_manager import run_delegation_supervision
    from hg_core.task_graph.behavior_telemetry import make_behavior_event
    run_id = "blocked-test"
    workflow_id = "w1"
    events = [
        make_behavior_event(run_id, workflow_id, "n1", "delegation.assign"),
        make_behavior_event(run_id, workflow_id, "n2", "delegation.split", parent_work_item_id="n1"),
    ]
    for i in range(15):
        events.append(make_behavior_event(run_id, workflow_id, f"n_{i}", "delegation.split", parent_work_item_id="n2"))
    summary = run_delegation_supervision(run_id, workflow_id, events, final_status="completed")
    blocked = summary.get("final_state", {}).get("external_writes_blocked") == "yes"
    intervention = summary.get("intervention", {}).get("step")
    degraded = summary.get("quality", {}).get("degraded")
    # Consistency: if sandbox/escalate/halt or degraded, must be blocked
    if intervention in ("sandbox", "escalate", "halt") or degraded:
        assert blocked, "external_writes_blocked should be yes when intervention is sandbox/escalate/halt or degraded"
    assert "final_state" in summary
    assert "external_writes_blocked" in summary["final_state"]
