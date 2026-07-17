"""MOR mortality closure checks for Batch L3-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.lifecycle.config import (
    mor_enabled,
    mor_forbid_process_kill,
    mor_forbid_successor_spawn,
    mor_refuse_stale_death_notice,
    mor_static_fixtures_only,
)
from hg_core.lifecycle.no_authority import check_lifecycle_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.mortality_memory_offering.events import planned_mor_event_refs


def run_mor_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "mortality_memory_offering"
    checks.append(PolicyBatchCheck("mor_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "mortality_memory_offering_gate.py"
    checks.append(PolicyBatchCheck("mor_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "mortality_memory_offering"
    checks.append(PolicyBatchCheck("mor_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "mortality_memory_offering" / "MOR_SPEC.md"
    checks.append(PolicyBatchCheck("mor_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_mor_event_refs()
    checks.append(
        PolicyBatchCheck(
            "mor_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "mor_static_fixtures_only_default",
            mor_static_fixtures_only(),
            "HG_MOR_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "mor_forbid_process_kill_default",
            mor_forbid_process_kill(),
            "HG_MOR_FORBID_PROCESS_KILL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "mor_forbid_successor_spawn_default",
            mor_forbid_successor_spawn(),
            "HG_MOR_FORBID_SUCCESSOR_SPAWN=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "mor_refuse_stale_death_notice_default",
            mor_refuse_stale_death_notice(),
            "HG_MOR_REFUSE_STALE_DEATH_NOTICE=1",
        )
    )

    fences_ok, fence_detail = check_lifecycle_import_fences()
    checks.append(
        PolicyBatchCheck("lifecycle_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "mor_disabled_by_default",
            not mor_enabled(),
            "HG_MOR_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "mor",
        "feature": "MOR",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_mor_closure_checks"]
