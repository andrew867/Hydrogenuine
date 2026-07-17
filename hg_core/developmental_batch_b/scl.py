"""SCL closure checks for Batch D4-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    scl_enabled,
    scl_refuse_stale_context,
    scl_refuse_unknown_strategy,
    scl_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.strategy_choice.events import planned_scl_event_refs


def run_scl_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "strategy_choice"
    checks.append(PolicyBatchCheck("scl_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "scl_strategy_choice_gate.py"
    checks.append(PolicyBatchCheck("scl_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "scl"
    checks.append(PolicyBatchCheck("scl_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "strategy_choice_layer" / "SCL_SPEC.md"
    checks.append(PolicyBatchCheck("scl_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_scl_event_refs()
    checks.append(
        PolicyBatchCheck(
            "scl_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "scl_static_fixtures_only_default",
            scl_static_fixtures_only(),
            "HG_SCL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "scl_refuse_stale_context_default",
            scl_refuse_stale_context(),
            "HG_SCL_REFUSE_STALE_CONTEXT=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "scl_refuse_unknown_strategy_default",
            scl_refuse_unknown_strategy(),
            "HG_SCL_REFUSE_UNKNOWN_STRATEGY=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "scl_disabled_by_default",
            not scl_enabled(),
            "HG_SCL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "scl",
        "feature": "SCL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_scl_closure_checks"]
