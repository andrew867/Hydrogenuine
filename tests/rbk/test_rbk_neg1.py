"""RBK-NEG1: compensable binding without drill_ref rejected at catalog load."""

from __future__ import annotations

import pytest

from pathlib import Path

from hg_core.capability_risk.catalog import CatalogEntry, _validate_entry, load_catalog

WORKSPACE = Path(__file__).resolve().parents[2]


def test_rbk_neg1_compensation_requires_drill_ref() -> None:
    entry = CatalogEntry(
        capability_id="rbk_neg1_test",
        name="test",
        description="compensable without drill",
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
    defaults = load_catalog(workspace=WORKSPACE).class_defaults_for("external")
    assert defaults is not None
    with pytest.raises(ValueError, match="drill_ref"):
        _validate_entry(entry, defaults)
