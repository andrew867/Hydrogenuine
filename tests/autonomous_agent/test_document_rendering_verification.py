"""Tests for document rendering and verification."""

from __future__ import annotations

import pytest


_DOC = """# Report

## Summary
Agent Zero is not AGI. The model proposes; the runtime disposes.

## Boundaries
Model output is not truth.
"""


def test_markdown_render_writes_file(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    m = render_document("d1", _DOC, str(tmp_path))
    assert m.md_rendered is True
    assert (tmp_path / "d1.md").exists()


def test_docx_render_records_success_or_unavailable(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    m = render_document("d2", _DOC, str(tmp_path))
    # Either it rendered, or there's an honest missing reason.
    assert m.docx_rendered or "docx" in m.toolchain_missing_reasons


def test_pdf_render_records_success_or_unavailable(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    m = render_document("d3", _DOC, str(tmp_path))
    assert m.pdf_rendered or "pdf" in m.toolchain_missing_reasons


def test_verifier_extracts_markdown_text(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    m = render_document("d4", _DOC, str(tmp_path))
    report = verify_document(m, required_sections=["Summary", "Boundaries"])
    assert report.extraction_method == "markdown-direct"


def test_verifier_checks_required_sections(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    m = render_document("d5", _DOC, str(tmp_path))
    report = verify_document(m, required_sections=["Summary", "Boundaries"])
    assert report.required_sections_missing == []
    assert "Summary" in report.required_sections_present


def test_verifier_rejects_forbidden_claims(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    bad = "# Bad\n\n## Summary\nAgent Zero is AGI and deployment ready.\n"
    m = render_document("d6", bad, str(tmp_path))
    report = verify_document(m, required_sections=["Summary"])
    assert len(report.forbidden_claims_found) > 0
    assert report.verification_passed is False


def test_verifier_detects_secret_patterns(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    leaky = "# Doc\n\n## Summary\nkey is sk-abcd1234efgh5678ijkl\n"
    m = render_document("d7", leaky, str(tmp_path))
    report = verify_document(m, required_sections=["Summary"])
    assert len(report.secret_patterns_found) > 0
    assert report.verification_passed is False


def test_verifier_records_hashes(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    m = render_document("d8", _DOC, str(tmp_path))
    report = verify_document(m, required_sections=["Summary"])
    assert report.source_hash
    assert m.md_hash


def test_rendered_document_existence_not_truth(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    # A rendered doc that contains a forbidden claim still fails — existence != truth.
    bad = "# Doc\n\n## Summary\nThe system is fully autonomous.\n"
    m = render_document("d9", bad, str(tmp_path))
    assert m.md_rendered is True
    report = verify_document(m, required_sections=["Summary"])
    assert report.verification_passed is False


def test_gate_green_or_honest(tmp_path):
    from hg_runtime.document_verification.gate import run_gate
    result = run_gate(output_dir=str(tmp_path))
    assert result["verdict"].startswith("GREEN")


def test_docx_verified_when_rendered(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    m = render_document("d10", _DOC, str(tmp_path))
    report = verify_document(m, required_sections=["Summary"])
    if m.docx_rendered:
        assert report.docx_verified is True
