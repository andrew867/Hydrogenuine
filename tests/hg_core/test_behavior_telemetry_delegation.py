"""
Tests for behavior telemetry and delegation graph (Autonomy Ch5 Phase 1).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from hg_core.task_graph.behavior_telemetry import (
    VALID_EVENT_TYPES,
    make_behavior_event,
    validate_behavior_event,
    emit_behavior_event,
)
from hg_core.task_graph.delegation_graph import (
    DelegationGraphBuilder,
    build_graph_from_events,
    persist_delegation_artifacts,
)


class TestValidateBehaviorEvent:
    """Event validation for required types and schema."""

    def test_valid_event_passes(self):
        event = make_behavior_event(
            run_id="r1", workflow_id="w1", work_item_id="n1", event_type="delegation.assign"
        )
        assert validate_behavior_event(event) == []

    def test_missing_required_field_fails(self):
        event = make_behavior_event(
            run_id="r1", workflow_id="w1", work_item_id="n1", event_type="delegation.assign"
        )
        del event["run_id"]
        errs = validate_behavior_event(event)
        assert any("run_id" in e for e in errs)

    def test_invalid_event_type_fails(self):
        event = make_behavior_event(
            run_id="r1", workflow_id="w1", work_item_id="n1", event_type="delegation.assign"
        )
        event["event_type"] = "invalid.type"
        errs = validate_behavior_event(event)
        assert any("event_type" in e for e in errs)

    def test_invalid_severity_fails(self):
        event = make_behavior_event(
            run_id="r1", workflow_id="w1", work_item_id="n1", event_type="delegation.assign"
        )
        event["severity"] = "invalid"
        errs = validate_behavior_event(event)
        assert any("severity" in e for e in errs)


class TestDelegationGraphBuilder:
    """Graph builder from event sequence; summary depth, width, handoffs, splits, merges."""

    def test_empty_events_produces_empty_graph(self):
        builder = DelegationGraphBuilder("r1", "w1", "root")
        graph = builder.to_graph_dict()
        summary = builder.to_summary_dict()
        assert graph["run_id"] == "r1"
        assert graph["nodes"] == []
        assert graph["edges"] == []
        assert summary["metrics"]["total_work_items"] == 0
        assert summary["metrics"]["handoff_count"] == 0
        assert summary["metrics"]["delegation_depth_max"] == 0

    def test_single_work_item(self):
        builder = DelegationGraphBuilder("r1", "w1")
        builder.ingest_event(
            make_behavior_event(
                run_id="r1", workflow_id="w1", work_item_id="n1",
                event_type="delegation.assign", agent_id="a1"
            )
        )
        graph = builder.to_graph_dict()
        summary = builder.to_summary_dict()
        assert len(graph["nodes"]) == 1
        assert graph["nodes"][0]["id"] == "n1"
        assert summary["metrics"]["total_work_items"] == 1
        assert summary["metrics"]["delegation_depth_max"] == 0

    def test_handoff_and_split_counts(self):
        events = [
            make_behavior_event("r1", "w1", "n1", "delegation.assign", agent_id="a1"),
            make_behavior_event("r1", "w1", "n2", "delegation.handoff", agent_id="a2", parent_work_item_id="n1"),
            make_behavior_event("r1", "w1", "n3", "delegation.split", agent_id="a1", parent_work_item_id="n1"),
        ]
        graph_dict, summary_dict = build_graph_from_events("r1", "w1", events)
        assert summary_dict["metrics"]["total_work_items"] == 3
        assert summary_dict["metrics"]["handoff_count"] == 1
        assert summary_dict["metrics"]["split_count"] == 1
        assert summary_dict["metrics"]["delegation_depth_max"] == 1
        assert len(graph_dict["edges"]) >= 2

    def test_depth_and_width(self):
        builder = DelegationGraphBuilder("r1", "w1")
        # root n1 -> n2, n3 (width 2), n2 -> n4 (depth 2)
        builder.ingest_event(make_behavior_event("r1", "w1", "n1", "delegation.assign", agent_id="a1"))
        builder.ingest_event(make_behavior_event("r1", "w1", "n2", "delegation.split", agent_id="a1", parent_work_item_id="n1"))
        builder.ingest_event(make_behavior_event("r1", "w1", "n3", "delegation.split", agent_id="a1", parent_work_item_id="n1"))
        builder.ingest_event(make_behavior_event("r1", "w1", "n4", "delegation.handoff", agent_id="a2", parent_work_item_id="n2"))
        summary = builder.to_summary_dict()
        assert summary["metrics"]["delegation_depth_max"] == 2
        assert summary["metrics"]["delegation_width_max"] >= 2
        assert summary["metrics"]["total_work_items"] == 4


class TestPersistDelegationArtifacts:
    """Integration: persist delegation_graph.json and delegation_summary.json to run_dir."""

    def test_persist_creates_files(self):
        with tempfile.TemporaryDirectory() as d:
            run_dir = Path(d)
            graph_dict = {"run_id": "r1", "workflow_id": "w1", "nodes": [], "edges": []}
            summary_dict = {
                "run_id": "r1", "workflow_id": "w1", "root_objective_summary": "",
                "metrics": {"delegation_depth_max": 0, "total_work_items": 0},
                "anomalies": [], "top_bottlenecks": [],
                "final_state": {"status": "success", "external_writes_attempted": "no", "external_writes_blocked": "no"},
            }
            persist_delegation_artifacts(run_dir, graph_dict, summary_dict)
            assert (run_dir / "delegation_graph.json").exists()
            assert (run_dir / "delegation_summary.json").exists()
            with open(run_dir / "delegation_summary.json", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["run_id"] == "r1"
            assert "metrics" in loaded

    def test_emit_behavior_event_writes_valid_line(self):
        event = make_behavior_event("r1", "w1", "n1", "delegation.assign")
        with tempfile.TemporaryDirectory() as d:
            run_dir = Path(d)
            path = run_dir / "behavior_events.jsonl"
            emit_behavior_event(run_dir, event, behavior_events_path=path)
            assert path.exists()
            with open(path, encoding="utf-8") as f:
                line = f.read().strip()
            loaded = json.loads(line)
            assert loaded["run_id"] == "r1"
            assert loaded["event_type"] == "delegation.assign"

    def test_emit_invalid_event_raises(self):
        with tempfile.TemporaryDirectory() as d:
            run_dir = Path(d)
            bad = {"run_id": "r1"}  # missing required fields
            with pytest.raises(ValueError):
                emit_behavior_event(run_dir, bad)


class TestExecutorIntegration:
    """Integration: run executor with run_dir asserts behavior stream and delegation summary exist."""

    def test_run_with_run_dir_produces_behavior_and_delegation_artifacts(self, tmp_path):
        from hg_core.task_graph import (
            DAG,
            Node,
            RunPolicy,
            NodePolicy,
            Checkpoints,
            TaskGraphExecutor,
        )
        from hg_core.task_graph.state_store import StateStore

        def _node(nid: str, depends_on: list = None) -> Node:
            return Node(
                id=nid,
                type="tool",
                assigned_entity="stub",
                depends_on=depends_on or [],
                inputs={},
                outputs={},
                policy=NodePolicy(),
                checkpoints=Checkpoints(),
            )
        dag = DAG(
            graph_id="delegation_test",
            version="1.0",
            run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
            inputs={"goal": "test"},
            nodes=[_node("a"), _node("b", ["a"]), _node("c", ["b"])],
        )
        run_dir = tmp_path / "run"
        store = StateStore(base_dir=tmp_path / "runs")
        exec = TaskGraphExecutor(
            dispatcher=lambda n, i: {"ok": True, "outputs": {}},
            state_store=store,
        )
        summary = exec.run(dag, run_dir=run_dir)
        assert summary.get("ok") is True
        assert (run_dir / "behavior_events.jsonl").exists()
        assert (run_dir / "delegation_graph.json").exists()
        assert (run_dir / "delegation_summary.json").exists()
        with open(run_dir / "behavior_events.jsonl", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) >= 1  # at least one delegation.assign (run emits per node started)
        with open(run_dir / "delegation_summary.json", encoding="utf-8") as f:
            ds = json.load(f)
        assert ds["run_id"] == summary["run_id"]
        assert ds["metrics"]["total_work_items"] >= 1


class TestDelegationQualityAndIntervention:
    """Phase 2: budget enforcement, quality checks, block external writes when degraded/sandbox/escalate/halt."""

    def test_budget_exceeded_applies_intervention(self):
        from hg_core.task_graph import intervention_policy as ip
        metrics = {
            "delegation_depth_max": 20,
            "total_work_items": 5,
            "split_count": 2,
            "handoff_count": 1,
        }
        budgets = {"max_delegation_depth": 15, "max_active_work_items": 100}
        exceeded = ip.which_budget_exceeded(metrics, budgets)
        assert exceeded == "max_delegation_depth"
        interv = ip.current_intervention(metrics, budgets=budgets)
        assert interv["step"] in ip.INTERVENTION_STEPS
        assert interv["exceeded_budget"] == "max_delegation_depth"
        assert interv["recorded"] is True

    def test_quality_below_threshold_marks_degraded(self):
        from hg_core.task_graph import delegation_quality as dq
        metrics = {"delegation_depth_max": 15, "delegation_width_max": 25, "total_work_items": 60}
        score = dq.delegation_quality_score(metrics)
        assert 0 <= score <= 1
        degraded = dq.is_run_degraded(score, threshold=0.9)
        assert degraded is True or score >= 0.9
        result = dq.check_quality(metrics, threshold=0.5)
        assert "score" in result and "degraded" in result

    def test_should_block_external_writes(self):
        from hg_core.task_graph import intervention_policy as ip
        assert ip.should_block_external_writes("sandbox", False) is True
        assert ip.should_block_external_writes("escalate", False) is True
        assert ip.should_block_external_writes("halt", False) is True
        assert ip.should_block_external_writes("warn", False) is False
        assert ip.should_block_external_writes("warn", True) is True


class TestEmergentBehaviorDetectors:
    """Phase 3: detector triggers D1/D3/D4; anomalies include evidence pointers; interventions deterministic."""

    def test_runaway_delegation_triggers_d1(self):
        from hg_core.task_graph import emergent_behavior_detectors as ebd
        metrics = {"delegation_depth_max": 15, "total_work_items": 5, "split_count": 0, "merge_count": 0}
        anomalies = ebd.run_detector_runaway_delegation(metrics)
        assert any(a["detector_id"] == "D1_runaway_delegation" for a in anomalies)
        for a in anomalies:
            assert "evidence" in a and "recommended_action" in a

    def test_looping_thrash_triggers_d3(self):
        from hg_core.task_graph import emergent_behavior_detectors as ebd
        metrics = {"retry_count": 8}
        node_attempts = {"n1": 4}
        anomalies = ebd.run_detector_looping_thrash(metrics, node_attempts)
        assert any(a["detector_id"] == "D3_looping_thrash" for a in anomalies)
        for a in anomalies:
            assert "evidence" in a

    def test_policy_pressure_triggers_d4(self):
        from hg_core.task_graph import emergent_behavior_detectors as ebd
        metrics = {}
        events = [
            {"event_type": "safety.blocked"},
            {"event_type": "safety.blocked"},
        ]
        anomalies = ebd.run_detector_policy_pressure(metrics, events)
        assert any(a["detector_id"] == "D4_policy_pressure" for a in anomalies)

    def test_run_detector_goal_drift_flags_mismatch(self):
        from hg_core.task_graph import emergent_behavior_detectors as ebd
        metrics = {"declared_goal": "post once", "goal_achieved": False}
        anomalies = ebd.run_detector_goal_drift(metrics, [])
        assert any(a["detector_id"] == "D2_goal_drift" for a in anomalies)
        assert any("review_goal" in a.get("recommended_action", "") for a in anomalies)

    def test_run_detector_cost_spike_flags_high_token_rate(self):
        from hg_core.task_graph import emergent_behavior_detectors as ebd
        metrics = {"token_rate_per_min": 10000}
        anomalies = ebd.run_detector_cost_spike(metrics)
        assert any(a["detector_id"] == "D5_cost_spike" for a in anomalies)
        assert any("cap_tokens" in a.get("recommended_action", "") for a in anomalies)

    def test_run_default_detectors_returns_anomalies_with_evidence(self):
        from hg_core.task_graph import emergent_behavior_detectors as ebd
        metrics = {"delegation_depth_max": 14, "retry_count": 7}
        events = [{"event_type": "safety.blocked"}, {"event_type": "safety.blocked"}]
        node_attempts = {"n1": 5}
        anomalies = ebd.run_default_detectors(metrics, events=events, node_attempts=node_attempts)
        assert isinstance(anomalies, list)
        for a in anomalies:
            assert "detector_id" in a and "severity" in a and "evidence" in a
            assert len(a["evidence"]) >= 1
