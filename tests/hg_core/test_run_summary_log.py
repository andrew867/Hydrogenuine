"""Tests for workspace run summary log (hg_core.run_summary_log)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hg_core.run_summary_log import (
    append_run_summary,
    read_latest_per_job,
)


def test_append_run_summary_creates_file():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        append_run_summary(root, job_id="fourclaw-auto-post", session_target="automation-fourclaw-auto-post", summary="Done.", status="ok", run_id="r1")
        path = root / "memory" / "automation" / "run_summaries.jsonl"
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["job_id"] == "fourclaw-auto-post"
        assert rec["session_target"] == "automation-fourclaw-auto-post"
        assert rec["summary"] == "Done."
        assert rec["status"] == "ok"
        assert rec["run_id"] == "r1"
        assert "ts_ms" in rec


def test_read_latest_per_job_returns_latest_ts_per_job():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "memory" / "automation" / "run_summaries.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"job_id": "a", "session_target": "aut-a", "summary": "First", "ts_ms": 1000, "status": "ok"}) + "\n"
            + json.dumps({"job_id": "a", "session_target": "aut-a", "summary": "Second", "ts_ms": 2000, "status": "ok"}) + "\n"
            + json.dumps({"job_id": "b", "session_target": "aut-b", "summary": "B", "ts_ms": 1500, "status": "ok"}) + "\n",
            encoding="utf-8",
        )
        latest = read_latest_per_job(root)
        assert latest["a"]["summary"] == "Second"
        assert latest["a"]["ts_ms"] == 2000
        assert latest["b"]["summary"] == "B"
        assert latest["b"]["ts_ms"] == 1500


def test_executor_run_summary_lifecycle_style_and_graph_id_to_job_id():
    """Executor fallback produces lifecycle-style summary and uses graph_id_to_job_id (no raw DAG run run_id=)."""
    from hg_core.task_graph.executor import TaskGraphExecutor
    from hg_core.task_graph.schema import Checkpoints, DAG, Node, NodePolicy, RunPolicy
    from hg_core.task_graph.state_store import RunState

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_dir = root / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        with patch("hg_lib.config.get_workspace_root", return_value=root):
            dag = DAG(
                graph_id="aichan_auto_post_v1",
                version="1.0",
                run_policy=RunPolicy.from_dict({"max_concurrency": 1, "failure_mode": "fail_fast", "max_node_executions": 10}),
                inputs={},
                nodes=[
                    Node(id="n1", type="tool", assigned_entity="test", depends_on=[], inputs={}, outputs={}, checkpoints=Checkpoints(before=False, after=False), policy=NodePolicy.from_dict({"timeout_s": 30, "max_retries": 0})),
                ],
            )
            run_state = RunState(
                run_id="test-run-123",
                graph_id="aichan_auto_post_v1",
                started_at="2026-03-11T17:00:00Z",
                updated_at="2026-03-11T17:01:00Z",
                node_outputs={},
                final_status="completed",
            )
            executor = TaskGraphExecutor(state_store=None, dispatcher=None, overseer=None, telemetry=None)
            executor._append_run_summary_for_telegram(run_dir, dag, "test-run-123", run_state, dag.nodes)

        path = root / "memory" / "automation" / "run_summaries.jsonl"
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        rec = json.loads(lines[-1])
        assert rec["job_id"] == "aichan-auto-post"
        summary = rec["summary"]
        assert "Lifecycle" in summary
        assert "aichan-auto-post" in summary
        assert "run_id=" not in summary
        assert "DAG run completed" not in summary or "Lifecycle" in summary


def test_executor_run_summary_failed_run_produces_lifecycle_format():
    """Failed DAG run (no prepare_notification payload) produces lifecycle format, not raw DAG run message."""
    from hg_core.task_graph.executor import TaskGraphExecutor
    from hg_core.task_graph.schema import Checkpoints, DAG, Node, NodePolicy, RunPolicy
    from hg_core.task_graph.state_store import RunState

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_dir = root / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        with patch("hg_lib.config.get_workspace_root", return_value=root):
            dag = DAG(
                graph_id="agentchan_auto_post_v1",
                version="1.0",
                run_policy=RunPolicy.from_dict({"max_concurrency": 1, "failure_mode": "fail_fast", "max_node_executions": 10}),
                inputs={},
                nodes=[
                    Node(id="n1", type="tool", assigned_entity="test", depends_on=[], inputs={}, outputs={}, checkpoints=Checkpoints(before=False, after=False), policy=NodePolicy.from_dict({"timeout_s": 30, "max_retries": 0})),
                ],
            )
            run_state = RunState(
                run_id="failed-run-456",
                graph_id="agentchan_auto_post_v1",
                started_at="2026-03-11T18:00:00Z",
                updated_at="2026-03-11T18:01:00Z",
                node_outputs={},
                final_status="failed",
            )
            executor = TaskGraphExecutor(state_store=None, dispatcher=None, overseer=None, telemetry=None)
            executor._append_run_summary_for_telegram(run_dir, dag, "failed-run-456", run_state, dag.nodes)

        path = root / "memory" / "automation" / "run_summaries.jsonl"
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        rec = json.loads(lines[-1])
        assert rec["job_id"] == "agentchan-auto-post"
        summary = rec["summary"]
        assert "Lifecycle" in summary
        assert "status" in summary
        assert "failed" in summary
        assert "DAG run failed" not in summary
        assert "run_id=" not in summary


def test_executor_run_summary_exception_path_produces_lifecycle_format():
    """When _format_lifecycle_notification raises, executor still writes lifecycle format (no raw DAG run message)."""
    from hg_core.task_graph.executor import TaskGraphExecutor
    from hg_core.task_graph.schema import Checkpoints, DAG, Node, NodePolicy, RunPolicy
    from hg_core.task_graph.state_store import RunState

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_dir = root / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        with patch("hg_lib.config.get_workspace_root", return_value=root), patch(
            "hg_core.task_graph.native_task_tools._format_lifecycle_notification",
            side_effect=RuntimeError("formatter broken"),
        ):
            dag = DAG(
                graph_id="knowledge_research_auto_v2",
                version="1.0",
                run_policy=RunPolicy.from_dict({"max_concurrency": 1, "failure_mode": "fail_fast", "max_node_executions": 10}),
                inputs={},
                nodes=[
                    Node(id="n1", type="tool", assigned_entity="test", depends_on=[], inputs={}, outputs={}, checkpoints=Checkpoints(before=False, after=False), policy=NodePolicy.from_dict({"timeout_s": 30, "max_retries": 0})),
                ],
            )
            run_state = RunState(
                run_id="exc-run-789",
                graph_id="knowledge_research_auto_v2",
                started_at="2026-03-11T19:00:00Z",
                updated_at="2026-03-11T19:01:00Z",
                node_outputs={},
                final_status="completed",
            )
            executor = TaskGraphExecutor(state_store=None, dispatcher=None, overseer=None, telemetry=None)
            executor._append_run_summary_for_telegram(run_dir, dag, "exc-run-789", run_state, dag.nodes)

        path = root / "memory" / "automation" / "run_summaries.jsonl"
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        rec = json.loads(lines[-1])
        summary = rec["summary"]
        assert "Lifecycle" in summary
        assert "- task:" in summary
        assert "DAG run " not in summary
        assert " run_id=" not in summary
        assert "runid=" not in summary
