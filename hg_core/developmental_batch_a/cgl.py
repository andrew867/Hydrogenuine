"""CGL closure checks for Batch D4-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    cgl_enabled,
    cgl_refuse_stale_edge,
    cgl_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.connection_governance.events import planned_cgl_event_refs


def run_cgl_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "connection_governance"
    checks.append(PolicyBatchCheck("cgl_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "cgl_connection_governance_gate.py"
    checks.append(PolicyBatchCheck("cgl_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "cgl"
    checks.append(PolicyBatchCheck("cgl_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "connection_governance_layer" / "CGL_SPEC.md"
    checks.append(PolicyBatchCheck("cgl_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_cgl_event_refs()
    checks.append(
        PolicyBatchCheck(
            "cgl_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "cgl_static_fixtures_only_default",
            cgl_static_fixtures_only(),
            "HG_CGL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "cgl_refuse_stale_edge_default",
            cgl_refuse_stale_edge(),
            "HG_CGL_REFUSE_STALE_EDGE=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "cgl_disabled_by_default",
            not cgl_enabled(),
            "HG_CGL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "cgl",
        "feature": "CGL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_cgl_closure_checks"]
