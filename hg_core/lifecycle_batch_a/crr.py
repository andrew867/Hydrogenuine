"""CRR integration alignment closure checks for Batch L3-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.lifecycle.config import (
    crr_alignment_enabled,
    crr_forbid_process_kill,
    crr_forbid_successor_spawn,
    crr_refuse_stale_alignment,
    crr_static_fixtures_only,
)
from hg_core.lifecycle.no_authority import check_lifecycle_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.coordinated_rest_recovery.events import planned_crr_event_refs


def run_crr_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "coordinated_rest_recovery"
    checks.append(PolicyBatchCheck("crr_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "coordinated_rest_recovery_gate.py"
    checks.append(PolicyBatchCheck("crr_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "coordinated_rest_recovery"
    checks.append(PolicyBatchCheck("crr_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    event_types = workspace / "hg_runtime" / "event_types_v1.yaml"
    event_text = event_types.read_text(encoding="utf-8") if event_types.is_file() else ""
    checks.append(
        PolicyBatchCheck(
            "crr_rtc_events_registered",
            "CRR_RECOVERY_CYCLE_STARTED:" in event_text,
            "event_types_v1.yaml",
        )
    )

    refs = planned_crr_event_refs()
    checks.append(
        PolicyBatchCheck(
            "crr_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "crr_static_fixtures_only_default",
            crr_static_fixtures_only(),
            "HG_CRR_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "crr_forbid_process_kill_default",
            crr_forbid_process_kill(),
            "HG_CRR_FORBID_PROCESS_KILL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "crr_forbid_successor_spawn_default",
            crr_forbid_successor_spawn(),
            "HG_CRR_FORBID_SUCCESSOR_SPAWN=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "crr_refuse_stale_default",
            crr_refuse_stale_alignment(),
            "HG_CRR_REFUSE_STALE_ALIGNMENT=1",
        )
    )

    fences_ok, fence_detail = check_lifecycle_import_fences()
    checks.append(
        PolicyBatchCheck("lifecycle_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "crr_alignment_disabled_by_default",
            not crr_alignment_enabled(),
            "HG_CRR_ALIGNMENT_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "crr",
        "feature": "CRR",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_crr_closure_checks"]
