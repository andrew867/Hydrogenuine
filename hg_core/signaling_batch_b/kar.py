"""KAR closure checks for Batch S5-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    kar_enabled,
    kar_refuse_residue_as_permission,
    kar_refuse_stale_residue,
    kar_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.karmic_action_residue.events import planned_kar_event_refs


def run_kar_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "karmic_action_residue"
    checks.append(PolicyBatchCheck("kar_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "karmic_action_residue_gate.py"
    checks.append(PolicyBatchCheck("kar_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "kar"
    checks.append(PolicyBatchCheck("kar_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "karmic_action_residue" / "KAR_SPEC.md"
    checks.append(PolicyBatchCheck("kar_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_kar_event_refs()
    checks.append(
        PolicyBatchCheck(
            "kar_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "kar_static_fixtures_only_default",
            kar_static_fixtures_only(),
            "HG_KAR_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "kar_refuse_stale_residue_default",
            kar_refuse_stale_residue(),
            "HG_KAR_REFUSE_STALE_RESIDUE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "kar_refuse_residue_as_permission_default",
            kar_refuse_residue_as_permission(),
            "HG_KAR_REFUSE_RESIDUE_AS_PERMISSION=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "kar_disabled_by_default",
            not kar_enabled(),
            "HG_KAR_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "kar",
        "feature": "KAR",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_kar_closure_checks"]
