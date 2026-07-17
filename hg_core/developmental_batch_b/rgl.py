"""RGL closure checks for Batch D4-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    rgl_enabled,
    rgl_refuse_compliance_as_permission,
    rgl_refuse_stale_rule,
    rgl_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.rule_governance.events import planned_rgl_event_refs


def run_rgl_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "rule_governance"
    checks.append(PolicyBatchCheck("rgl_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "rgl_rule_governance_gate.py"
    checks.append(PolicyBatchCheck("rgl_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "rgl"
    checks.append(PolicyBatchCheck("rgl_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "rule_governance_layer" / "RGL_SPEC.md"
    checks.append(PolicyBatchCheck("rgl_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_rgl_event_refs()
    checks.append(
        PolicyBatchCheck(
            "rgl_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "rgl_static_fixtures_only_default",
            rgl_static_fixtures_only(),
            "HG_RGL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rgl_refuse_stale_rule_default",
            rgl_refuse_stale_rule(),
            "HG_RGL_REFUSE_STALE_RULE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rgl_refuse_compliance_as_permission_default",
            rgl_refuse_compliance_as_permission(),
            "HG_RGL_REFUSE_COMPLIANCE_AS_PERMISSION=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "rgl_disabled_by_default",
            not rgl_enabled(),
            "HG_RGL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rgl",
        "feature": "RGL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_rgl_closure_checks"]
