"""Phase 13 E2E: 10-agent search and analyze-50-files swarm workflows; zero TODOs/stubs in L10/DAG paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hg_realtime.swarm import SwarmController, SwarmPlan, SwarmResult


def _make_plan(tasks: list, max_children: int = 100, correlation_id: str = "e2e") -> SwarmPlan:
    return SwarmPlan(
        summary="E2E swarm",
        tasks=tasks,
        max_children=max_children,
        max_tool_calls_per_child=50,
        max_wall_clock_s_per_child=60,
        correlation_id=correlation_id,
        tenant_id="e2e",
        actor_id="e2e",
    )


def test_e2e_swarm_10_agent_search(tmp_path: Path) -> None:
    """E2E: Trigger web-search style swarm with 10 search tasks; assert 10 child runs, reduce completes, artifact has aggregated result."""
    # 10 search.query tasks (L10 tool); no DAG launcher needed
    tasks = [
        {"tool_name": "search.query", "args": {"q": f"query-{i}"}}
        for i in range(10)
    ]
    plan = _make_plan(tasks, max_children=10)
    mock_launcher = MagicMock()
    controller = SwarmController(launcher=mock_launcher, workspace=tmp_path)

    result = controller.run(plan)

    assert isinstance(result, SwarmResult)
    assert result.counts["completed"] == 10
    assert result.counts["failed"] == 0
    assert len(result.child_outputs) == 10
    assert result.status == "completed"
    assert result.artifacts_path is not None
    assert Path(result.artifacts_path).exists()
    payload = json.loads(Path(result.artifacts_path).read_text(encoding="utf-8"))
    assert payload.get("status") == "completed"
    assert payload.get("counts", {}).get("completed") == 10
    assert "summary" in payload
    assert "artifacts" in payload
    assert payload["artifacts"].get("child_count") == 10
    mock_launcher.launch.assert_not_called()


def test_e2e_swarm_analyze_50_files(tmp_path: Path) -> None:
    """E2E: Trigger analyze-files style swarm with 50 file.parse tasks; assert 50 parse jobs, reduce completes, artifact."""
    # Create 50 temp files under workspace so file.parse can read them
    files_dir = tmp_path / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    for i in range(50):
        (files_dir / f"doc_{i:02d}.txt").write_text(f"content-{i}", encoding="utf-8")

    tasks = [
        {"tool_name": "file.parse", "args": {"path": f"files/doc_{i:02d}.txt", "workspace": str(tmp_path)}}
        for i in range(50)
    ]
    plan = _make_plan(tasks, max_children=50)
    mock_launcher = MagicMock()
    controller = SwarmController(launcher=mock_launcher, workspace=tmp_path)

    result = controller.run(plan)

    assert isinstance(result, SwarmResult)
    assert result.counts["completed"] == 50
    assert result.counts["failed"] == 0
    assert len(result.child_outputs) == 50
    assert result.status == "completed"
    assert result.artifacts_path is not None
    assert Path(result.artifacts_path).exists()
    payload = json.loads(Path(result.artifacts_path).read_text(encoding="utf-8"))
    assert payload.get("status") == "completed"
    assert payload.get("counts", {}).get("completed") == 50
    assert payload["artifacts"].get("child_count") == 50
    mock_launcher.launch.assert_not_called()
