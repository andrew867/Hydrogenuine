"""Dashboard PDF must generate a real file (reportlab/matplotlib) for overseer monitor."""

from pathlib import Path


def test_generate_dashboard_pdf_writes_valid_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    overseer_dir = tmp_path / "memory" / "overseer"
    overseer_dir.mkdir(parents=True)

    from hg_overseer.overseer_core.dashboard_pdf_generator import generate_dashboard_pdf

    pdf_path = generate_dashboard_pdf([], include_summaries=False, lightweight=True)
    assert pdf_path is not None
    path = Path(pdf_path)
    assert path.exists(), f"PDF not created at {pdf_path}"
    assert path.stat().st_size > 100
    assert path.read_bytes()[:4] == b"%PDF"
