"""IIL closure checks for Batch D4-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    iil_enabled,
    iil_fail_closed_physical_blast,
    iil_refuse_unknown_blast_radius,
    iil_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.interconnected_impact.events import planned_iil_event_refs


def run_iil_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "interconnected_impact"
    checks.append(PolicyBatchCheck("iil_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "iil_interconnected_impact_gate.py"
    checks.append(PolicyBatchCheck("iil_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "iil"
    checks.append(PolicyBatchCheck("iil_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "interconnected_impact_layer" / "IIL_SPEC.md"
    checks.append(PolicyBatchCheck("iil_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_iil_event_refs()
    checks.append(
        PolicyBatchCheck(
            "iil_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "iil_static_fixtures_only_default",
            iil_static_fixtures_only(),
            "HG_IIL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "iil_refuse_unknown_blast_radius_default",
            iil_refuse_unknown_blast_radius(),
            "HG_IIL_REFUSE_UNKNOWN_BLAST_RADIUS=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "iil_fail_closed_physical_blast_default",
            iil_fail_closed_physical_blast(),
            "HG_IIL_FAIL_CLOSED_PHYSICAL_BLAST=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "iil_disabled_by_default",
            not iil_enabled(),
            "HG_IIL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "iil",
        "feature": "IIL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_iil_closure_checks"]
