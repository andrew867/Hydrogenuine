"""
Pack 12: Test docs_summarize_10_to_docx proof and verifier. Requires office deps (python-docx, pypdf, reportlab).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.mark.skipif(
    not any(
        (REPO_ROOT / "hg_core" / "docs" / p).exists()
        for p in ["parsers/pdf_parser.py", "retrieval.py", "office/docx_tool.py"]
    ),
    reason="hg_core.docs parsers/retrieval/office not present",
)
def test_docs_summarize_10_to_docx_proof_run(tmp_path: Path) -> None:
    """Run proof in-process; assert artifacts and checks_passed."""
    # reportlab is imported deep inside run() (_make_minimal_pdfs); guard here so the
    # test skips cleanly in hermetic CI where reportlab is not installed, instead of
    # erroring. (CCS2 env guard.)
    pytest.importorskip("reportlab", reason="requires reportlab; absent in hermetic CI")
    try:
        from scripts.proofs.docs_summarize_10_to_docx import run
    except ImportError as e:
        if "reportlab" in str(e):
            pytest.skip("reportlab required for docs_summarize_10_to_docx proof")
        raise
    summary = run(tmp_path)
    assert summary.get("checks_passed") is True, summary
    artifacts = tmp_path / "artifacts"
    assert (artifacts / "DOCS_INPUT_INDEX.json").exists()
    assert (artifacts / "MAP_SUMMARIES.jsonl").exists()
    assert (artifacts / "REDUCE_SUMMARY.md").exists()
    assert (artifacts / "CITATION_VERIFY.json").exists()
    docx_path = tmp_path / "Executive_Summary_10_Docs.docx"
    if not docx_path.exists():
        docx_path = artifacts / "Executive_Summary_10_Docs.docx"
    assert docx_path.exists(), "Executive_Summary_10_Docs.docx not found"
    index = json.loads((artifacts / "DOCS_INPUT_INDEX.json").read_text(encoding="utf-8"))
    assert len(index) >= 10

    from docs.proofs.verify_docs_summarize_10_to_docx import verify
    ok, errs = verify(tmp_path)
    assert ok, errs
