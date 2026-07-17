"""DEP-BOND slice closure checks for Batch R2-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import dep_bond_enabled, dep_bond_refuse_stale_observation
from hg_runtime.dependency_attachment_boundary.events import planned_rtc_events


def run_dep_bond_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "dependency_attachment_boundary"
    checks.append(PolicyBatchCheck("dep_bond_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "dependency_attachment_boundary_gate.py"
    checks.append(PolicyBatchCheck("dep_bond_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "dependency_attachment_boundary"
    checks.append(PolicyBatchCheck("dep_bond_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    events = planned_rtc_events()
    checks.append(
        PolicyBatchCheck(
            "dep_bond_rtc_event_design_present",
            len(events) >= 7,
            f"planned_events={len(events)}",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "dep_bond_rtc_events_no_authority_fields",
            all(not e.get("authority_fields") for e in events),
            "all events authority_fields=False",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "dep_bond_refuse_stale_default",
            dep_bond_refuse_stale_observation(),
            "HG_DEP_BOND_REFUSE_STALE_OBSERVATION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "dep_bond_disabled_by_default",
            not dep_bond_enabled(),
            "HG_DEP_BOND_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "dep_bond",
        "feature": "DEP-BOND",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_dep_bond_closure_checks"]
