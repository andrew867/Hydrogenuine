"""IAB closure checks for Batch D4-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    iab_enabled,
    iab_refuse_inference_as_consent,
    iab_refuse_stale_other_model,
    iab_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.inter_awareness_boundary.events import planned_iab_event_refs


def run_iab_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "inter_awareness_boundary"
    checks.append(PolicyBatchCheck("iab_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "iab_inter_awareness_boundary_gate.py"
    checks.append(PolicyBatchCheck("iab_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "iab"
    checks.append(PolicyBatchCheck("iab_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "inter_awareness_boundary" / "IAB_SPEC.md"
    checks.append(PolicyBatchCheck("iab_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_iab_event_refs()
    checks.append(
        PolicyBatchCheck(
            "iab_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "iab_static_fixtures_only_default",
            iab_static_fixtures_only(),
            "HG_IAB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "iab_refuse_stale_other_model_default",
            iab_refuse_stale_other_model(),
            "HG_IAB_REFUSE_STALE_OTHER_MODEL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "iab_refuse_inference_as_consent_default",
            iab_refuse_inference_as_consent(),
            "HG_IAB_REFUSE_INFERENCE_AS_CONSENT=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "iab_disabled_by_default",
            not iab_enabled(),
            "HG_IAB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "iab",
        "feature": "IAB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_iab_closure_checks"]
