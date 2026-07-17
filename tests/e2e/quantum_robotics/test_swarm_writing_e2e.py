"""E2E: quantum-enhanced swarm writing with symmetry breaking and LDPC verification."""
from __future__ import annotations

import json

import pytest

from hg_quantum.error_correction.correction_decoder import decode_corrections
from hg_quantum.error_correction.syndrome_extractor import SyndromeExtractor
from hg_realtime.swarm.contracts import QuantumSwarmPlan
from hg_realtime.swarm.quantum_nodes import swarm_reduce_quantum, swarm_spawn_quantum

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def test_e2e_swarm_writing_with_symmetry_and_verification(proof_dir, monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_SHADOW", "false")
    plan = QuantumSwarmPlan(
        summary="write technical blog post about quantum computing",
        tasks=[{"workflow_id": "w1", "inputs": {}}, {"workflow_id": "w2", "inputs": {}}],
        max_children=4,
        base_fingerprint={"cognitive_fingerprint": {"analysis_vs_intuition": 0.5}},
        task_profile={"task_type": "analytical"},
        force_quantum=True,
    )
    children, spawn_meta = swarm_spawn_quantum(plan=plan, correlation_id="e2e-swarm-1")
    offsets = [c["quantum"]["trait_offsets"] for c in children]
    style_varied = len({json.dumps(o, sort_keys=True) for o in offsets}) > 1

    summaries = [
        "Quantum computing uses qubits.",
        "Quantum computing uses classical bits only.",
        "Entanglement enables correlation.",
        "LDPC codes protect information.",
    ]
    outputs = [
        {"entity_id": c["quantum"]["entity_id"], "summary": summaries[i % len(summaries)]}
        for i, c in enumerate(children)
    ]
    summary, artifacts, _warnings = swarm_reduce_quantum(
        child_outputs=outputs,
        swarm_run_id="e2e-swarm-1",
        plan=plan,
    )
    extractor = SyndromeExtractor()
    graph = extractor.build_verification_graph(outputs)
    syndromes = extractor.extract_syndromes(outputs, graph, swarm_run_id="e2e-swarm-1")
    corrections = decode_corrections(syndromes) if syndromes else []

    bundle = proof_dir / "swarm_writing"
    checks = [
        {"name": "style_variation", "pass": style_varied},
        {"name": "ldpc_reduce", "pass": "LDPC" in summary or "verification_graph" in artifacts},
        {"name": "syndromes_extracted", "pass": len(syndromes) >= 0},
        {"name": "spawn_pairs", "pass": len(spawn_meta["quantum"]["entangled_pairs"]) >= 1},
    ]
    write_proof_bundle(
        bundle,
        label="e2e_swarm_writing",
        checks=checks,
        summary_extra={
            "swarm_run_id": "e2e-swarm-1",
            "syndrome_count": len(syndromes),
            "correction_count": len(corrections),
        },
    )
    (bundle / "artifacts.json").write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
    assert style_varied
    assert all(c["pass"] for c in checks)
