"""E2E: strategic-loss intervention near exceptional point (governed)."""
from __future__ import annotations

import pytest

from hg_quantum.non_hermitian.exceptional_point_detector import ExceptionalPointDetector

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def test_e2e_strategic_loss_intervention(proof_dir):
    det = ExceptionalPointDetector()
    points = det.scan({
        "context_usage": 0.92,
        "swarm_size": 14,
        "drift_score": 0.75,
        "retry_count": 6,
        "coordination_overhead": 0.85,
    })
    pending = det.pending_interventions()
    governed = [p for p in pending if p["status"] == "pending_approval"]

    bundle = proof_dir / "strategic_loss"
    checks = [
        {"name": "phase_transitions_detected", "pass": len(points) >= 1},
        {"name": "interventions_governed", "pass": len(governed) == len(pending) and len(pending) >= 1},
        {"name": "requires_approval", "pass": all(p.get("status") == "pending_approval" for p in pending)},
    ]
    write_proof_bundle(
        bundle,
        label="e2e_strategic_loss_intervention",
        checks=checks,
        summary_extra={"interventions": pending},
    )
    assert all(c["pass"] for c in checks)
