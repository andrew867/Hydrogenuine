"""Batch CT-B RBK-NEG1 pack closure tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.capability_risk.catalog import CatalogEntry, _validate_entry, load_catalog
from hg_core.pack_closure.checks import run_pack_closure_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_rbk_neg1_closure_checks_green() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="rbk_neg1")
    assert result["ok"], result.get("critical_failures", result)


def test_unsupported_pack_fails_closed() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="tim_full")
    assert not result["ok"]
    assert "unsupported_pack" in result["critical_failures"]


def test_compensable_without_drill_ref_rejected() -> None:
    catalog = load_catalog(workspace=WORKSPACE)
    defaults = catalog.class_defaults_for("external")
    assert defaults is not None
    entry = CatalogEntry(
        capability_id="rbk_neg1_adversarial",
        name="adversarial",
        description="must fail",
        risk_class="external",
        status="real_gated",
        dry_run_mode="required",
        compensation="partial",
        compensation_required=True,
        drill_ref=None,
        required_evidence=(),
        required_authority=(),
        min_review_tier="high_risk",
    )
    with pytest.raises(ValueError, match="drill_ref"):
        _validate_entry(entry, defaults)


def test_live_catalog_has_no_compensable_without_drill_ref() -> None:
    catalog = load_catalog(workspace=WORKSPACE)
    violators = [
        e.capability_id
        for e in catalog.capabilities
        if e.compensation_required and e.compensation != "none" and not e.drill_ref
    ]
    assert violators == []
