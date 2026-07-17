"""CNT continuity boundary closure checks for Batch L3-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.lifecycle.config import (
    cnt_enabled,
    cnt_refuse_identity_continuity,
    cnt_refuse_stale_authority_inheritance,
    cnt_static_fixtures_only,
)
from hg_core.lifecycle.no_authority import check_lifecycle_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.continuity_boundary.events import planned_cnt_event_refs


def run_cnt_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "continuity_boundary"
    checks.append(PolicyBatchCheck("cnt_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "continuity_boundary_gate.py"
    checks.append(PolicyBatchCheck("cnt_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "continuity_boundary"
    checks.append(PolicyBatchCheck("cnt_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "continuity_boundary" / "CNT_SPEC.md"
    checks.append(PolicyBatchCheck("cnt_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_cnt_event_refs()
    checks.append(
        PolicyBatchCheck(
            "cnt_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "cnt_static_fixtures_only_default",
            cnt_static_fixtures_only(),
            "HG_CNT_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "cnt_refuse_identity_continuity_default",
            cnt_refuse_identity_continuity(),
            "HG_CNT_REFUSE_IDENTITY_CONTINUITY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "cnt_refuse_stale_authority_inheritance_default",
            cnt_refuse_stale_authority_inheritance(),
            "HG_CNT_REFUSE_STALE_AUTHORITY_INHERITANCE=1",
        )
    )

    fences_ok, fence_detail = check_lifecycle_import_fences()
    checks.append(
        PolicyBatchCheck("lifecycle_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "cnt_disabled_by_default",
            not cnt_enabled(),
            "HG_CNT_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "cnt",
        "feature": "CNT",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_cnt_closure_checks"]
