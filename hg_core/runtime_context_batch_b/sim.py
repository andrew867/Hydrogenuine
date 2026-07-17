"""SIM slice closure checks for Batch R2-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import sim_enabled, sim_offline_only, sim_refuse_stale_scenario
from hg_runtime.simulated_outcome_rehearsal.events import planned_rtc_events


def run_sim_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "simulated_outcome_rehearsal"
    checks.append(PolicyBatchCheck("sim_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "simulated_outcome_rehearsal_gate.py"
    checks.append(PolicyBatchCheck("sim_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "simulated_outcome_rehearsal"
    checks.append(PolicyBatchCheck("sim_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    events = planned_rtc_events()
    checks.append(
        PolicyBatchCheck(
            "sim_rtc_event_design_present",
            len(events) >= 8,
            f"planned_events={len(events)}",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sim_rtc_events_no_authority_fields",
            all(not e.get("authority_fields") for e in events),
            "all events authority_fields=False",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "sim_refuse_stale_default",
            sim_refuse_stale_scenario(),
            "HG_SIM_REFUSE_STALE_SCENARIO=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sim_offline_only_default",
            sim_offline_only(),
            "HG_SIM_OFFLINE_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sim_disabled_by_default",
            not sim_enabled(),
            "HG_SIM_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "sim",
        "feature": "SIM",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_sim_closure_checks"]
