from pathlib import Path

from scripts.proofs.retention_replay_demo import run
from scripts.verify_proof_bundle import verify_bundle


def test_retention_replay_demo_bundle(tmp_path: Path):
    outdir = tmp_path / "retention_replay_demo"
    outdir.mkdir(parents=True, exist_ok=True)
    summary = run(outdir)
    assert summary["checks_passed"] is True
    assert (outdir / "REDACT_PREVIEW.json").exists()
    assert (outdir / "BEFORE_PURGE.json").exists()
    assert (outdir / "AFTER_PURGE.json").exists()
    assert (outdir / "TIMELINE_EVENTS.json").exists()
    assert (outdir / "EVIDENCE_LEDGER.json").exists()
    ok, errors = verify_bundle(outdir, label="retention_replay_demo")
    assert ok, errors
