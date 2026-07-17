"""Batch CT-C full final CT audit tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.ct_acceptance.final_audit import run_ct_full_final_audit_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_full_final_audit_checks_green() -> None:
    result = run_ct_full_final_audit_checks(WORKSPACE)
    assert result["ok"], result.get("critical_failures", result)


def test_full_audit_report_present() -> None:
    result = run_ct_full_final_audit_checks(WORKSPACE)
    by_id = {c["check_id"]: c for c in result["checks"]}
    assert by_id["full_final_audit_report_green"]["ok"]


def test_full_audit_includes_reconcile_and_milestone() -> None:
    result = run_ct_full_final_audit_checks(WORKSPACE)
    assert result["reconcile"]["ok"]
    assert result["milestone"]["ok"]
