"""Phase 5: Swarm controller tests — spawn 3 children (3 launch calls + reduce), cap 200 with max_children=10."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

import pytest

from hg_realtime.swarm import SwarmController, SwarmPlan, SwarmResult
from hg_realtime.scheduler.models import RunRequested


def _make_plan(tasks: list, max_children: int = 10, correlation_id: str = "test-c") -> SwarmPlan:
    return SwarmPlan(
        summary="test swarm",
        tasks=tasks,
        max_children=max_children,
        max_tool_calls_per_child=50,
        max_wall_clock_s_per_child=300,
        correlation_id=correlation_id,
        tenant_id="test",
        actor_id="test",
    )


def test_swarm_spawn_three_children_three_launch_calls_and_reduce(tmp_path: Path) -> None:
    """Spawn 3 children: assert 3 launch calls and reduce with 3 outputs."""
    launch_calls: list = []
    run_ids = [str(uuid.uuid4()) for _ in range(3)]

    def record_launch(req: RunRequested) -> str:
        launch_calls.append(req)
        return run_ids[len(launch_calls) - 1]

    mock_launcher = MagicMock()
    mock_launcher.launch.side_effect = record_launch

    plan = _make_plan(
        [
            {"workflow_id": "job-a", "inputs": {"x": 1}},
            {"workflow_id": "job-b", "inputs": {"x": 2}},
            {"workflow_id": "job-c", "inputs": {"x": 3}},
        ],
        max_children=10,
    )
    controller = SwarmController(launcher=mock_launcher, workspace=tmp_path)

    with patch.object(controller, "_wait_for_run", return_value=(True, {"ok": True, "outputs": {}})):
        result = controller.run(plan)

    assert len(launch_calls) == 3
    assert result.counts["launched"] == 3
    assert result.counts["completed"] == 3
    assert result.counts["failed"] == 0
    assert len(result.child_run_ids) == 3
    assert result.child_run_ids == run_ids
    assert len(result.child_outputs) == 3
    assert result.status == "completed"
    assert result.artifacts_path is not None
    assert Path(result.artifacts_path).exists()


def test_swarm_cap_200_children_max_10_only_10_launched(tmp_path: Path) -> None:
    """Cap 200 children with max_children=10 → only 10 launched."""
    launch_calls: list = []

    def record_launch(req: RunRequested) -> str:
        launch_calls.append(req)
        return str(uuid.uuid4())

    mock_launcher = MagicMock()
    mock_launcher.launch.side_effect = record_launch

    # 200 tasks, max_children=10
    tasks = [{"workflow_id": "job-x", "inputs": {"i": i}} for i in range(200)]
    plan = _make_plan(tasks, max_children=10)
    controller = SwarmController(launcher=mock_launcher, workspace=tmp_path)

    with patch.object(controller, "_wait_for_run", return_value=(True, {"ok": True})):
        result = controller.run(plan)

    assert len(launch_calls) == 10
    assert result.counts["launched"] == 10
    assert len(result.child_run_ids) == 10


def test_swarm_max_100_cap_enforced(tmp_path: Path) -> None:
    """Even with 150 tasks and max_children=150, hard cap 100 → only 100 launched."""
    launch_calls: list = []

    def record_launch(req: RunRequested) -> str:
        launch_calls.append(req)
        return str(uuid.uuid4())

    mock_launcher = MagicMock()
    mock_launcher.launch.side_effect = record_launch

    tasks = [{"workflow_id": "job-x", "inputs": {"i": i}} for i in range(150)]
    plan = _make_plan(tasks, max_children=150)  # plan wants 150
    controller = SwarmController(launcher=mock_launcher, workspace=tmp_path)

    with patch.object(controller, "_wait_for_run", return_value=(True, {"ok": True})):
        result = controller.run(plan)

    assert len(launch_calls) == 100
    assert result.counts["launched"] == 100
