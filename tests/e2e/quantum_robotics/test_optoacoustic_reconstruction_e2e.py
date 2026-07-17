"""E2E: optoacoustic proof reconstruction without live mesh."""
from __future__ import annotations

import pytest

from hg_quantum.persistence.optoacoustic_linker import OptoacousticLinker

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def test_e2e_optoacoustic_reconstruction(proof_dir, tmp_path):
    linker = OptoacousticLinker(fingerprint_id="fp_e2e", store_dir=tmp_path / "oa")
    events = []
    for i in range(3):
        mesh = {"event_id": f"mesh-{i}", "type": "job_progress", "ts": float(i), "fingerprint_id": "fp_e2e"}
        proof = {"snapshot_id": f"proof-{i}", "type": "swarm_proof", "seq": i}
        linker.link_mesh_to_proof(mesh, proof)
        events.append(proof["snapshot_id"])

    timeline = linker.reconstruct_from_proof_trail(events)
    bundle = proof_dir / "optoacoustic"
    checks = [
        {"name": "reconstruct_count", "pass": len(timeline) == 3},
        {"name": "ordered_timeline", "pass": timeline[0]["mesh_event"]["ts"] <= timeline[-1]["mesh_event"]["ts"]},
        {"name": "no_live_mesh_required", "pass": all("mesh_event_id" in t for t in timeline)},
    ]
    write_proof_bundle(bundle, label="e2e_optoacoustic_reconstruction", checks=checks)
    assert all(c["pass"] for c in checks)
