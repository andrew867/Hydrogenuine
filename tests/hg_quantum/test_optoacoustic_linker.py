from __future__ import annotations

from pathlib import Path

from hg_quantum.persistence.optoacoustic_linker import OptoacousticLinker


def test_link_and_reconstruct(tmp_path):
    linker = OptoacousticLinker(fingerprint_id="fp_test", store_dir=tmp_path / "links")
    mesh = {"event_id": "m1", "type": "job_progress", "ts": 100.0, "fingerprint_id": "fp_test"}
    proof = {"snapshot_id": "p1", "type": "run_proof"}
    link = linker.link_mesh_to_proof(mesh, proof)
    assert linker.resolve_mesh_event("m1") is not None
    assert linker.resolve_proof_snapshot("p1") is not None
    timeline = linker.reconstruct_from_proof_trail(["p1"])
    assert len(timeline) == 1
    assert timeline[0]["mesh_event_id"] == "m1"
