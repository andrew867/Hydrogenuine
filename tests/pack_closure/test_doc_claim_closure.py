"""Batch CT-B DOC claim chain pack closure tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.docs_freshness.scanner import run_claim_check
from hg_core.pack_closure.checks import run_pack_closure_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_doc_claim_closure_checks_green() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="doc_claim_chain")
    assert result["ok"], result.get("critical_failures", result)


def test_live_claim_check_passes_without_fixtures() -> None:
    report = run_claim_check(WORKSPACE)
    assert report.ok
    assert report.citation_lint.get("ok", False)


def test_doc_claim_chain_reports_pack17() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="doc_claim_chain")
    assert result["pack"] == "doc_claim_chain"
    assert "CT-17" in result["packs"]
