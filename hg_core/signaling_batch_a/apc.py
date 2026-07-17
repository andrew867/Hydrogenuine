"""APC closure checks for Batch S5-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    apc_enabled,
    apc_refuse_cue_as_truth,
    apc_refuse_stale_cue,
    apc_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.ambient_proximity_cues.events import planned_apc_event_refs


def run_apc_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "ambient_proximity_cues"
    checks.append(PolicyBatchCheck("apc_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "ambient_proximity_cues_gate.py"
    checks.append(PolicyBatchCheck("apc_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "apc"
    checks.append(PolicyBatchCheck("apc_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "ambient_proximity_cues" / "APC_SPEC.md"
    checks.append(PolicyBatchCheck("apc_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_apc_event_refs()
    checks.append(
        PolicyBatchCheck(
            "apc_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "apc_static_fixtures_only_default",
            apc_static_fixtures_only(),
            "HG_APC_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "apc_refuse_stale_cue_default",
            apc_refuse_stale_cue(),
            "HG_APC_REFUSE_STALE_CUE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "apc_refuse_cue_as_truth_default",
            apc_refuse_cue_as_truth(),
            "HG_APC_REFUSE_CUE_AS_TRUTH=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "apc_disabled_by_default",
            not apc_enabled(),
            "HG_APC_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "apc",
        "feature": "APC",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_apc_closure_checks"]
