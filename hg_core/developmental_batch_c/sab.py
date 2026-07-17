"""SAB closure checks for Batch D4-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    sab_enabled,
    sab_refuse_operator_absence_as_consent,
    sab_refuse_stale_self_model,
    sab_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.self_awareness_boundary.events import planned_sab_event_refs


def run_sab_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "self_awareness_boundary"
    checks.append(PolicyBatchCheck("sab_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "sab_self_awareness_boundary_gate.py"
    checks.append(PolicyBatchCheck("sab_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "sab"
    checks.append(PolicyBatchCheck("sab_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "self_awareness_boundary" / "SAB_SPEC.md"
    checks.append(PolicyBatchCheck("sab_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_sab_event_refs()
    checks.append(
        PolicyBatchCheck(
            "sab_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "sab_static_fixtures_only_default",
            sab_static_fixtures_only(),
            "HG_SAB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sab_refuse_stale_self_model_default",
            sab_refuse_stale_self_model(),
            "HG_SAB_REFUSE_STALE_SELF_MODEL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sab_refuse_operator_absence_as_consent_default",
            sab_refuse_operator_absence_as_consent(),
            "HG_SAB_REFUSE_OPERATOR_ABSENCE_AS_CONSENT=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "sab_disabled_by_default",
            not sab_enabled(),
            "HG_SAB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "sab",
        "feature": "SAB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_sab_closure_checks"]
