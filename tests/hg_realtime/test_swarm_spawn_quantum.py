from __future__ import annotations

import os

import pytest

from hg_realtime.swarm.contracts import QuantumSwarmPlan, SwarmPlan
from hg_realtime.swarm.quantum_nodes import swarm_reduce_quantum, swarm_spawn_quantum


@pytest.fixture(autouse=True)
def _enable_quantum_flags(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_SYMMETRY_BREAKING_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_ENABLED", "true")


def test_swarm_spawn_quantum_differentiates_children():
    plan = QuantumSwarmPlan(
        summary="test",
        tasks=[{"workflow_id": "w1", "inputs": {}}, {"workflow_id": "w2", "inputs": {}}],
        max_children=2,
        base_fingerprint={"cognitive_fingerprint": {"analysis_vs_intuition": 0.5}},
        task_profile={"task_type": "analytical"},
        force_quantum=True,
    )
    children, meta = swarm_spawn_quantum(plan=plan, correlation_id="corr-1")
    assert len(children) == 2
    assert meta["quantum"]["enabled"] is True
    assert children[0]["quantum"]["trait_offsets"]
    assert children[0]["quantum"]["trait_offsets"] != children[1]["quantum"]["trait_offsets"]


def test_shadow_mode_takes_no_action_on_reduce(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_SHADOW", "true")
    outputs = [
        {"entity_id": "a", "summary": "alpha"},
        {"entity_id": "b", "summary": "beta different"},
    ]
    summary, artifacts, _warnings = swarm_reduce_quantum(
        child_outputs=outputs,
        swarm_run_id="swarm-1",
        plan=QuantumSwarmPlan(summary="t", tasks=[], force_quantum=True),
    )
    assert "Reduced 2 child outputs" in summary
    assert "quantum_shadow" in artifacts


def test_swarm_reduce_quantum_active_mode_summary(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_SHADOW", "false")
    outputs = [
        {"entity_id": "a", "summary": "same"},
        {"entity_id": "b", "summary": "same"},
    ]
    summary, artifacts, _ = swarm_reduce_quantum(
        child_outputs=outputs,
        swarm_run_id="swarm-2",
        plan=QuantumSwarmPlan(summary="t", tasks=[], force_quantum=True),
    )
    assert "LDPC-verified" in summary
    assert "verification_graph" in artifacts


def test_classic_plan_unchanged_without_flags(monkeypatch):
    monkeypatch.delenv("HG_QUANTUM_SYMMETRY_BREAKING_ENABLED", raising=False)
    monkeypatch.delenv("HG_QUANTUM_LDPC_VERIFICATION_ENABLED", raising=False)
    plan = SwarmPlan(summary="classic", tasks=[{"workflow_id": "w", "inputs": {}}])
    children, meta = swarm_spawn_quantum(plan=plan, correlation_id="c1")
    assert meta["quantum"]["enabled"] is False
    assert "quantum" not in children[0]
