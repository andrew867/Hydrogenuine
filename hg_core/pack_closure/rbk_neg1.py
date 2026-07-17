"""RBK-NEG1 pack closure — compensable catalog entries require drill_ref."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.capability_risk.catalog import CatalogEntry, _validate_entry, load_catalog
from hg_core.pack_closure.types import PackClosureCheck


def _bad_compensable_entry() -> CatalogEntry:
    return CatalogEntry(
        capability_id="rbk_neg1_closure_probe",
        name="closure probe",
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


def run_rbk_neg1_closure_checks(workspace: Path) -> dict[str, Any]:
    """Verify RBK-NEG1 negative drill is proven, not skipped or normalized."""
    checks: list[PackClosureCheck] = []

    test_path = workspace / "tests" / "rbk" / "test_rbk_neg1.py"
    checks.append(
        PackClosureCheck(
            "rbk_neg1_test_present",
            test_path.is_file(),
            str(test_path.relative_to(workspace)).replace("\\", "/"),
        )
    )

    rbk_gate = workspace / "scripts" / "evals" / "rollback_drill_gate.py"
    gate_text = rbk_gate.read_text(encoding="utf-8") if rbk_gate.is_file() else ""
    checks.append(
        PackClosureCheck(
            "rbk_gate_documents_neg1",
            "test_rbk_neg1.py" in gate_text,
            "rollback_drill_gate cites unit test",
        )
    )

    catalog = load_catalog(workspace=workspace)
    violators = [
        entry.capability_id
        for entry in catalog.capabilities
        if entry.compensation_required and entry.compensation != "none" and not entry.drill_ref
    ]
    checks.append(
        PackClosureCheck(
            "catalog_compensable_have_drill_ref",
            not violators,
            f"violators={violators}" if violators else f"entries={len(catalog.capabilities)}",
        )
    )

    defaults = catalog.class_defaults_for("external")
    rejected = False
    detail = "no external defaults"
    if defaults is not None:
        try:
            _validate_entry(_bad_compensable_entry(), defaults)
            detail = "bad entry accepted"
        except ValueError as exc:
            rejected = "drill_ref" in str(exc)
            detail = str(exc)
    checks.append(
        PackClosureCheck(
            "validate_entry_rejects_missing_drill_ref",
            rejected,
            detail,
        )
    )

    enforce_path = workspace / "hg_core" / "capability_risk" / "enforce.py"
    enforce_text = enforce_path.read_text(encoding="utf-8") if enforce_path.is_file() else ""
    checks.append(
        PackClosureCheck(
            "no_catalog_to_execution_authority",
            "not grant" in enforce_text.lower() or "read_only" in enforce_text.lower(),
            "catalog remains classification-only",
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "pack": "rbk_neg1",
        "packs": ("CT-07", "CT-12"),
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_rbk_neg1_closure_checks"]
