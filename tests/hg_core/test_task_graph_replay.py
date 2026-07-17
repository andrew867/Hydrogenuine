"""Tests for DAG deterministic replay: recording and replay harness."""

import json
import tempfile
from pathlib import Path

import pytest

from hg_core.task_graph import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    TaskGraphExecutor,
)
from hg_core.task_graph.recording import AttemptRecorder
from hg_core.task_graph.replay_dispatcher import ReplayConfig, make_replay_adapter


def _node(nid: str, depends_on: list = None, node_type: str = "eval") -> Node:
    return Node(
        id=nid,
        type=node_type,
        assigned_entity="evaluator",
        depends_on=depends_on or [],
        inputs={"expression": "1 + 1", "output_key": "x"} if node_type == "eval" else {},
        outputs={"x": 2} if node_type == "eval" else {},
        policy=NodePolicy(),
        checkpoints=Checkpoints(),
    )


def _dag(nodes: list) -> DAG:
    return DAG(
        graph_id="replay_test",
        version="1.0",
        run_policy=RunPolicy(max_concurrency=1, failure_mode="fail_fast"),
        inputs={},
        nodes=nodes,
    )


def test_recorder_creates_attempts_file():
    """AttemptRecorder creates recordings/attempts.jsonl with request/response pairs and expected keys."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        recorder = AttemptRecorder(str(run_dir), "run-1", "graph-1")
        token = recorder.record_request(
            node_id="n1",
            attempt_no=1,
            request={"type": "eval", "assigned_entity": "evaluator", "resolved_inputs": {"expression": "1"}},
        )
        recorder.record_response(
            token,
            {"ok": True, "outputs": {"x": 1}},
            error=None,
        )
        path = run_dir / "recordings" / "attempts.jsonl"
        assert path.exists()
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 2
        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["kind"] == "request"
        assert r1["run_id"] == "run-1"
        assert r1["graph_id"] == "graph-1"
        assert r1["node_id"] == "n1"
        assert r1["attempt_no"] == 1
        assert "request_digest" in r1
        assert r2["kind"] == "response"
        assert "response_digest" in r2


def test_executor_with_recorder_writes_attempts():
    """Executor with run_dir and recorder yields recordings/attempts.jsonl with request/response pairs."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = _dag([_node("a"), _node("b", ["a"])])
        run_id = "run-rec"
        recorder = AttemptRecorder(str(run_dir), run_id, dag.graph_id)
        executor = TaskGraphExecutor(recorder=recorder)
        summary = executor.run(dag, run_dir=run_dir, run_id=run_id)
        assert summary.get("ok") is True
        path = run_dir / "recordings" / "attempts.jsonl"
        assert path.exists()
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= 2
        kinds = [json.loads(ln)["kind"] for ln in lines]
        assert "request" in kinds
        assert "response" in kinds
        for rec in [json.loads(ln) for ln in lines]:
            assert rec.get("run_id") == run_id
            assert rec.get("graph_id") == dag.graph_id
            if rec["kind"] == "request":
                assert "request_digest" in rec
            else:
                assert "response_digest" in rec


def test_executor_without_recorder_no_recordings():
    """Executor with run_dir but no recorder does not create recordings dir."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = _dag([_node("a")])
        executor = TaskGraphExecutor()
        summary = executor.run(dag, run_dir=run_dir)
        assert summary.get("ok") is True
        rec_dir = run_dir / "recordings"
        assert not rec_dir.exists()


def test_record_then_replay_same_summary():
    """Record a run with live dispatcher + recorder, then replay with ReplayDispatcher; summary matches."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = _dag([_node("a"), _node("b", ["a"])])
        run_id = "run-replay"
        recorder = AttemptRecorder(str(run_dir), run_id, dag.graph_id)
        executor = TaskGraphExecutor(recorder=recorder)
        summary_live = executor.run(dag, run_dir=run_dir, run_id=run_id)
        assert summary_live.get("ok") is True
        assert (run_dir / "recordings" / "attempts.jsonl").exists()

        replay_dispatcher = make_replay_adapter(str(run_dir))
        executor_replay = TaskGraphExecutor(dispatcher=replay_dispatcher)
        summary_replay = executor_replay.run(dag, run_dir=run_dir, run_id=run_id + "-replay")
        assert summary_replay.get("ok") is True

        assert summary_replay.get("final_status") == summary_live.get("final_status")
        nodes_live = summary_live.get("nodes", {})
        nodes_replay = summary_replay.get("nodes", {})
        for nid in nodes_live:
            assert nid in nodes_replay
            assert nodes_replay[nid].get("status") == nodes_live[nid].get("status")
        assert summary_replay.get("node_outputs") == summary_live.get("node_outputs")


def test_record_then_replay_identical_outcomes():
    """Integration: record then replay yields identical terminal statuses and outputs."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = _dag([_node("a"), _node("b", ["a"])])
        run_id = "run-ident"
        recorder = AttemptRecorder(str(run_dir), run_id, dag.graph_id)
        executor = TaskGraphExecutor(recorder=recorder)
        summary_live = executor.run(dag, run_dir=run_dir, run_id=run_id)
        assert summary_live.get("ok") is True

        replay_dispatcher = make_replay_adapter(str(run_dir), ReplayConfig(strict_requests=True))
        executor_replay = TaskGraphExecutor(dispatcher=replay_dispatcher)
        summary_replay = executor_replay.run(dag, run_dir=run_dir, run_id=run_id + "-replay")
        assert summary_replay.get("ok") is True

        assert summary_replay.get("final_status") == summary_live.get("final_status")
        for nid in summary_live.get("nodes", {}):
            assert summary_replay["nodes"][nid]["status"] == summary_live["nodes"][nid]["status"]
        assert summary_replay.get("node_outputs") == summary_live.get("node_outputs")


def test_strict_replay_request_digest_mismatch_raises():
    """Strict replay: modified request digest causes replay to fail (ValueError from dispatcher)."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        dag = _dag([_node("a")])
        run_id = "run-strict"
        recorder = AttemptRecorder(str(run_dir), run_id, dag.graph_id)
        executor = TaskGraphExecutor(recorder=recorder)
        executor.run(dag, run_dir=run_dir, run_id=run_id)

        # Tamper: change one request_digest in attempts.jsonl
        path = run_dir / "recordings" / "attempts.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        tampered = []
        for line in lines:
            if line.strip():
                rec = json.loads(line)
                if rec.get("kind") == "request" and "request_digest" in rec:
                    rec["request_digest"] = "tampered"
                tampered.append(json.dumps(rec, ensure_ascii=False))
        path.write_text("\n".join(tampered) + "\n", encoding="utf-8")

        replay_dispatcher = make_replay_adapter(str(run_dir), ReplayConfig(strict_requests=True))
        executor_replay = TaskGraphExecutor(dispatcher=replay_dispatcher)
        summary_replay = executor_replay.run(dag, run_dir=run_dir, run_id=run_id + "-replay")
        # Executor catches dispatch ValueError and sets node.error; run fails
        assert summary_replay.get("ok") is False
        assert summary_replay.get("final_status") == "failed"
        node_a = summary_replay.get("nodes", {}).get("a", {})
        assert "Request digest mismatch" in str(node_a.get("error", ""))
