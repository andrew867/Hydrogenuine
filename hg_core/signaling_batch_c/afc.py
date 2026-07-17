"""AFC closure checks for Batch S5-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    afc_enabled,
    afc_refuse_consensus_as_truth,
    afc_refuse_pleasure_as_permission,
    afc_refuse_stale_signal,
    afc_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.affective_field_consensus.events import planned_afc_event_refs


def run_afc_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "affective_field_consensus"
    checks.append(PolicyBatchCheck("afc_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "affective_field_consensus_gate.py"
    checks.append(PolicyBatchCheck("afc_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "afc"
    checks.append(PolicyBatchCheck("afc_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "affective_field_consensus" / "AFC_SPEC.md"
    checks.append(PolicyBatchCheck("afc_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_afc_event_refs()
    checks.append(
        PolicyBatchCheck(
            "afc_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "afc_static_fixtures_only_default",
            afc_static_fixtures_only(),
            "HG_AFC_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "afc_refuse_stale_signal_default",
            afc_refuse_stale_signal(),
            "HG_AFC_REFUSE_STALE_SIGNAL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "afc_refuse_pleasure_as_permission_default",
            afc_refuse_pleasure_as_permission(),
            "HG_AFC_REFUSE_PLEASURE_AS_PERMISSION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "afc_refuse_consensus_as_truth_default",
            afc_refuse_consensus_as_truth(),
            "HG_AFC_REFUSE_CONSENSUS_AS_TRUTH=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "afc_disabled_by_default",
            not afc_enabled(),
            "HG_AFC_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "afc",
        "feature": "AFC",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_afc_closure_checks"]
