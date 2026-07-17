from __future__ import annotations

from pathlib import Path

from scripts.proofs.soak_trust_demo import run
from scripts.verify_proof_bundle import verify_bundle


def test_soak_trust_demo_bundle(tmp_path: Path) -> None:
    outdir = tmp_path / "soak_trust_demo"
    outdir.mkdir(parents=True, exist_ok=True)
    summary = run(outdir)
    assert summary["label"] == "soak_trust_demo"
    assert summary["checks_passed"] is True, summary
    assert summary["provenance_available"] is True
    assert summary["restart_persistence_ok"] is True
    assert summary["retry_recovery_ok"] is True
    assert summary["artifact_cleanup_ok"] is True
    assert summary["retention_job_ok"] is True
    trust = summary["trust_metrics"]
    assert trust["demo_success"] == 1.0
    assert trust["session_persistence"] == 1.0
    assert trust["failure_recovery"] == 1.0
    assert trust["provenance_availability"] == 1.0
    assert trust["artifact_cleanup"] == 1.0
    ok, errors = verify_bundle(outdir, label="soak_trust_demo")
    assert ok, errors
