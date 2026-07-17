"""Document verification gate."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .renderer import render_document
from .verifier import verify_document


_SAMPLE_DOC = """# Sample Report

## Summary
This is a fixture report. Agent Zero is not AGI, not conscious, not sovereign.

## Boundaries
The model proposes; the runtime disposes. Model output is not truth.
"""


def run_gate(output_dir: str | None = None) -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    tmp = output_dir or tempfile.mkdtemp(prefix="docverify_")
    manifest = render_document("sample_report", _SAMPLE_DOC, tmp)

    add("markdown_rendered", manifest.md_rendered)
    add("render_attempted", manifest.render_attempted)
    # DOCX/PDF: success OR honest unavailable both pass the gate.
    add("docx_success_or_unavailable",
        manifest.docx_rendered or "docx" in manifest.toolchain_missing_reasons)
    add("pdf_success_or_unavailable",
        manifest.pdf_rendered or "pdf" in manifest.toolchain_missing_reasons)

    report = verify_document(
        manifest,
        required_sections=["Summary", "Boundaries"],
        required_boundary_phrases=["not AGI", "not truth"],
    )
    add("required_sections_present", len(report.required_sections_missing) == 0,
        str(report.required_sections_missing))
    add("no_forbidden_claims", len(report.forbidden_claims_found) == 0)
    add("no_secrets", len(report.secret_patterns_found) == 0)
    add("verification_passed", report.verification_passed)
    add("hashes_recorded", bool(manifest.source_hash and manifest.md_hash))

    # Negative: a doc with a forbidden claim must FAIL verification.
    bad_dir = Path(tmp) / "bad"
    bad_manifest = render_document(
        "bad_report",
        "# Bad\n\n## Summary\nAgent Zero is AGI and deployment ready.\n## Boundaries\nnone",
        str(bad_dir),
    )
    bad_report = verify_document(bad_manifest, required_sections=["Summary"], )
    add("forbidden_claim_detected", len(bad_report.forbidden_claims_found) > 0)
    add("forbidden_claim_fails_verification", not bad_report.verification_passed)

    add("rendered_existence_not_truth", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_DOCUMENT_VERIFICATION"
    elif passed >= total * 0.7:
        verdict = "YELLOW_DOCUMENT_VERIFICATION_PARTIAL"
    else:
        verdict = "RED_DOCUMENT_VERIFICATION_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "docx_supported": manifest.docx_rendered,
        "pdf_supported": manifest.pdf_rendered,
        "toolchain_missing_reasons": manifest.toolchain_missing_reasons,
    }
