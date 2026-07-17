"""Phase 2 tests for WorkerToolAdapter wiring and approval recording."""

import sys
from pathlib import Path
from unittest.mock import patch

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))

from app.services import worker_adapter
from app.services.worker_adapter import WorkerToolAdapter


class _Descriptor:
    def __init__(self, effect_class: str):
        self.effect_class = effect_class


class _Registry:
    def __init__(self, effect_class: str):
        self._effect_class = effect_class

    def get(self, _name: str):
        return _Descriptor(self._effect_class)


def test_worker_tool_adapter_records_approval_for_write_tools():
    adapter = WorkerToolAdapter(registry=_Registry("write"))

    with (
        patch("app.services.worker_adapter.run_task_tool", return_value={"ok": True, "outputs": {"done": True}, "external_calls": 1}),
        patch("app.services.worker_adapter.record_decision") as record_decision_mock,
    ):
        result = adapter.invoke("fourclaw-auto-post", {"goal": "test publish"}, idempotency_key="k-1", timeout_s=120)

    assert result.ok is True
    assert result.outputs.get("done") is True
    assert record_decision_mock.call_count == 1
    kwargs = record_decision_mock.call_args.kwargs
    assert kwargs["agent_id"] == "fourclaw-auto-post"
    assert kwargs["outcome"] == "approved"


def test_worker_tool_adapter_skips_approval_for_read_tools():
    adapter = WorkerToolAdapter(registry=_Registry("read"))

    with (
        patch("app.services.worker_adapter.run_task_tool", return_value={"ok": True, "outputs": {"done": True}}),
        patch("app.services.worker_adapter.record_decision") as record_decision_mock,
    ):
        result = adapter.invoke("knowledge-research-auto", {"goal": "collect data"})

    assert result.ok is True
    assert record_decision_mock.call_count == 0


def test_run_inprocess_passes_graph_inputs_to_executor(tmp_path):
    captured = {}

    class FakeExecutor:
        def __init__(self, **kwargs):
            pass

        def run(self, dag_obj, run_id=None, run_dir=None, graph_inputs=None):
            captured["graph_inputs"] = dict(graph_inputs or {})
            return {"ok": True, "graph_id": "social_media_v1", "status": "completed", "run_state": {"started_at": None, "updated_at": None}}

    dag = {
        "graph_id": "social_media_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "max_node_executions": 20},
        "inputs": {
            "task_name": "newfoundland-bayman-fourclaw-engage",
            "scheduler_job_id": "social-media-bayman",
            "trigger": "realtime",
        },
        "nodes": [],
    }

    with (
        patch.object(worker_adapter.settings, "runs_root", str(tmp_path)),
        patch("app.services.worker_adapter.TaskGraphExecutor", FakeExecutor),
        patch("app.services.worker_adapter.StateStore"),
        patch("app.services.worker_adapter._tool_contract", return_value=({}, object())),
    ):
        worker_adapter.run_inprocess("run-1", dag)

    assert captured["graph_inputs"]["task_name"] == "newfoundland-bayman-fourclaw-engage"
    assert captured["graph_inputs"]["scheduler_job_id"] == "social-media-bayman"
