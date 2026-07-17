"""Phase 4 integration: adapter-produced approvals/dedup are reflected by API endpoints."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.worker_adapter import WorkerToolAdapter
    from hg_core.task_graph.tool_adapter import NativeTaskToolAdapter
else:  # pragma: no cover
    app = None
    TestClient = None
    WorkerToolAdapter = None
    NativeTaskToolAdapter = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    return TestClient(app)


class _Descriptor:
    def __init__(self, effect_class: str):
        self.effect_class = effect_class


class _Registry:
    def __init__(self, effect_class: str):
        self._effect_class = effect_class

    def get(self, _name: str):
        return _Descriptor(self._effect_class)


def test_phase4_end_to_end_approval_and_dedup_consistency(client, tmp_path):
    workflow_id = "fourclaw-auto-post"
    env_workspace = str(tmp_path)
    old_workspace = os.environ.get("HG_WORKSPACE")
    os.environ["HG_WORKSPACE"] = env_workspace
    try:
        with patch(
            "app.services.worker_adapter.run_task_tool",
            return_value={"ok": True, "outputs": {"published": True}, "external_calls": 1},
        ):
            worker_adapter = WorkerToolAdapter(registry=_Registry("write"))
            worker_result = worker_adapter.invoke(
                workflow_id,
                {"goal": "phase4 publish"},
                idempotency_key="phase4-idem",
                timeout_s=120,
            )
            assert worker_result.ok is True

        with patch(
            "hg_core.task_graph.tool_adapter.run_task_tool",
            return_value={"ok": True, "outputs": {"thread_id": "phase4-thread"}, "external_calls": 1},
        ):
            native_adapter = NativeTaskToolAdapter()
            first = native_adapter.invoke(
                workflow_id,
                {"goal": "phase4 native publish"},
                idempotency_key="phase4-idem",
                timeout_s=120,
            )
            second = native_adapter.invoke(
                workflow_id,
                {"goal": "phase4 native publish"},
                idempotency_key="phase4-idem",
                timeout_s=120,
            )
            assert first.ok is True
            assert second.ok is True
            assert isinstance(second.metadata, dict)
            assert second.metadata.get("dedupe_hit") is True

        run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "wf_phase4" / "run_1"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(
            json.dumps(
                {
                    "run_id": "run-phase4-1",
                    "graph_id": workflow_id,
                    "final_status": "completed",
                    "started_at": "2026-02-27T13:00:00Z",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        approvals_response = client.get(
            f"/api/v1/operator/approvals?workflow_id={workflow_id}&limit=20",
            headers=_headers(),
        )
        assert approvals_response.status_code == 200
        approvals_data = approvals_response.json()
        assert approvals_data.get("ok") is True
        assert approvals_data.get("total", 0) >= 1
        assert any(item.get("workflow_id") == workflow_id for item in approvals_data.get("items", []))

        dedup_response = client.get(
            f"/api/v1/workflows/{workflow_id}/dedup?limit=20",
            headers=_headers(),
        )
        assert dedup_response.status_code == 200
        dedup_data = dedup_response.json()
        assert dedup_data.get("ok") is True
        assert dedup_data.get("workflow_id") == workflow_id
        assert dedup_data.get("total", 0) >= 1
        assert any(item.get("idempotency_key") == "phase4-idem" for item in dedup_data.get("items", []))
        run_summary = dedup_data.get("run_summary", {})
        assert run_summary.get("latest_run_id") == "run-phase4-1"
    finally:
        if old_workspace is None:
            os.environ.pop("HG_WORKSPACE", None)
        else:
            os.environ["HG_WORKSPACE"] = old_workspace
