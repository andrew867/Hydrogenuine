from __future__ import annotations

from pathlib import Path

from scripts.soak_confidence_run import main


def test_soak_confidence_run_writes_report(tmp_path: Path, monkeypatch):
    outdir = tmp_path / "soak_out"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    code = main(["--iterations", "2", "--sleep-seconds", "0", "--outdir", str(outdir)])
    assert code == 0
    report_path = outdir / "soak_confidence_report.json"
    assert report_path.exists()
    data = __import__("json").loads(report_path.read_text(encoding="utf-8"))
    assert data["checks_passed"] is True
    assert data["iterations_passed"] == 2
    assert (tmp_path / "docs" / "proofs" / "audits" / "latest_soak_confidence.json").exists()
