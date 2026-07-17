"""SwarmController invokes swarm_spawn_quantum when quantum flags are on."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hg_realtime.swarm.contracts import QuantumSwarmPlan
from hg_realtime.swarm.controller import SwarmController


@pytest.fixture(autouse=True)
def _enable_quantum_spawn(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_SYMMETRY_BREAKING_ENABLED", "true")


def test_swarm_controller_merges_quantum_spawn_payload(monkeypatch, tmp_path: Path):
    launched_inputs = []

    class FakeLauncher:
        def launch(self, rr):
            launched_inputs.append(dict(rr.resolved_inputs))
            return "run-child-1"

    controller = SwarmController(
        launcher=FakeLauncher(),
        workspace=tmp_path,
        poll_interval_s=0.01,
    )
    plan = QuantumSwarmPlan(
        summary="quantum controller test",
        tasks=[{"workflow_id": "wf-1", "inputs": {"seed": 1}}],
        max_children=1,
        force_quantum=True,
        base_fingerprint={"cognitive_fingerprint": {"analysis_vs_intuition": 0.5}},
        task_profile={"task_type": "analytical"},
    )

    def fake_wait(self, run_id, workflow_id, deadline):
        return True, {"run_id": run_id, "status": "completed", "summary": "ok"}

    monkeypatch.setattr(SwarmController, "_wait_for_run", fake_wait)

    result = controller.run(plan)
    assert result.status == "completed"
    assert result.artifacts.get("quantum_spawn", {}).get("quantum", {}).get("enabled") is True
    assert launched_inputs
    assert "quantum" in launched_inputs[0]
