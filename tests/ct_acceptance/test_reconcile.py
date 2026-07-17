"""Batch CT-C acceptance reconciliation tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.ct_acceptance.reconcile import (
    REQUIRED_PHASE_REPORTS,
    run_ct_acceptance_reconcile,
    _inventory_open_blockers,
    _inventory_claims_no_open_abc,
)

WORKSPACE = Path(__file__).resolve().parents[2]


def test_acceptance_reconcile_green() -> None:
    result = run_ct_acceptance_reconcile(WORKSPACE)
    assert result["ok"], result.get("critical_failures", result)


def test_required_reports_list_complete() -> None:
    phases = WORKSPACE / "docs" / "reports" / "phases"
    missing = [name for name in REQUIRED_PHASE_REPORTS if not (phases / name).is_file()]
    assert not missing, missing


def test_inventory_no_open_abc_blockers() -> None:
    text = (WORKSPACE / "docs/reports/phases/CT_DEFERRED_ITEM_INVENTORY.md").read_text(encoding="utf-8")
    assert not _inventory_open_blockers(text)
    assert _inventory_claims_no_open_abc(text)


def test_fake_open_blocker_detected() -> None:
    sample = """
| D-99 | Fake | source | **A** | CT | **Open** | plan | proof |
"""
    assert len(_inventory_open_blockers(sample)) >= 1


def test_proof_bundles_have_evidence() -> None:
    result = run_ct_acceptance_reconcile(WORKSPACE)
    assert result["proof_bundles"]
    assert all(p["ok"] for p in result["proof_bundles"]), result["proof_bundles"]
