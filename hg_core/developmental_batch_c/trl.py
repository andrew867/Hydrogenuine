"""TRL closure checks for Batch D4-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    trl_enabled,
    trl_refuse_stale_snapshot,
    trl_refuse_summary_as_proof,
    trl_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.transparent_reality.events import planned_trl_event_refs


def run_trl_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "transparent_reality"
    checks.append(PolicyBatchCheck("trl_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "trl_transparent_reality_gate.py"
    checks.append(PolicyBatchCheck("trl_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "trl"
    checks.append(PolicyBatchCheck("trl_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "transparent_reality_layer" / "TRL_SPEC.md"
    checks.append(PolicyBatchCheck("trl_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_trl_event_refs()
    checks.append(
        PolicyBatchCheck(
            "trl_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "trl_static_fixtures_only_default",
            trl_static_fixtures_only(),
            "HG_TRL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "trl_refuse_stale_snapshot_default",
            trl_refuse_stale_snapshot(),
            "HG_TRL_REFUSE_STALE_SNAPSHOT=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "trl_refuse_summary_as_proof_default",
            trl_refuse_summary_as_proof(),
            "HG_TRL_REFUSE_SUMMARY_AS_PROOF=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "trl_disabled_by_default",
            not trl_enabled(),
            "HG_TRL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "trl",
        "feature": "TRL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_trl_closure_checks"]
