"""NEG closure checks for Batch S5-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    neg_enabled,
    neg_refuse_stale_observation,
    neg_refuse_surveillance_risk,
    neg_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.neglect_detection.events import planned_neg_event_refs


def run_neg_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "neglect_detection"
    checks.append(PolicyBatchCheck("neg_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "neglect_detection_gate.py"
    checks.append(PolicyBatchCheck("neg_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "neg"
    checks.append(PolicyBatchCheck("neg_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "neglect_detection" / "NEG_SPEC.md"
    checks.append(PolicyBatchCheck("neg_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_neg_event_refs()
    checks.append(
        PolicyBatchCheck(
            "neg_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "neg_static_fixtures_only_default",
            neg_static_fixtures_only(),
            "HG_NEG_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "neg_refuse_stale_observation_default",
            neg_refuse_stale_observation(),
            "HG_NEG_REFUSE_STALE_OBSERVATION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "neg_refuse_surveillance_risk_default",
            neg_refuse_surveillance_risk(),
            "HG_NEG_REFUSE_SURVEILLANCE_RISK=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "neg_disabled_by_default",
            not neg_enabled(),
            "HG_NEG_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "neg",
        "feature": "NEG",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_neg_closure_checks"]
