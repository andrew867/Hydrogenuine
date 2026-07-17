"""DNI closure checks for Batch D4-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    dni_enabled,
    dni_refuse_missing_evidence_high_urgency,
    dni_refuse_unknown_need,
    dni_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.desire_need_intake.events import planned_dni_event_refs


def run_dni_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "desire_need_intake"
    checks.append(PolicyBatchCheck("dni_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "dni_desire_need_intake_gate.py"
    checks.append(PolicyBatchCheck("dni_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "dni"
    checks.append(PolicyBatchCheck("dni_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "desire_need_intake" / "DNI_SPEC.md"
    checks.append(PolicyBatchCheck("dni_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_dni_event_refs()
    checks.append(
        PolicyBatchCheck(
            "dni_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "dni_static_fixtures_only_default",
            dni_static_fixtures_only(),
            "HG_DNI_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "dni_refuse_unknown_need_default",
            dni_refuse_unknown_need(),
            "HG_DNI_REFUSE_UNKNOWN_NEED=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "dni_refuse_missing_evidence_high_urgency_default",
            dni_refuse_missing_evidence_high_urgency(),
            "HG_DNI_REFUSE_MISSING_EVIDENCE_HIGH_URGENCY=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "dni_disabled_by_default",
            not dni_enabled(),
            "HG_DNI_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "dni",
        "feature": "DNI",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_dni_closure_checks"]
