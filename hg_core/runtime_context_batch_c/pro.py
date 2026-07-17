"""PRO slice + backburner closure checks for Batch R2-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import (
    pro_backburner_guard,
    pro_enabled,
    pro_hardware_allowed,
    pro_refuse_stale_body_state,
    pro_static_fixtures_only,
)
from hg_core.runtime_context.no_authority import check_runtime_import_fences
from hg_runtime.proprioceptive_body_model.backburner import assert_pro_backburner_boundary
from hg_runtime.proprioceptive_body_model.events import planned_rtc_events


def run_pro_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "proprioceptive_body_model"
    checks.append(PolicyBatchCheck("pro_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "proprioceptive_body_model_gate.py"
    checks.append(PolicyBatchCheck("pro_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "proprioceptive_body_model"
    checks.append(PolicyBatchCheck("pro_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    events = planned_rtc_events()
    checks.append(
        PolicyBatchCheck(
            "pro_rtc_event_design_present",
            len(events) >= 9,
            f"planned_events={len(events)}",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pro_rtc_events_no_authority_fields",
            all(not e.get("authority_fields") for e in events),
            "all events authority_fields=False",
        )
    )

    backburner = assert_pro_backburner_boundary()
    checks.append(
        PolicyBatchCheck(
            "pro_backburner_guard_default",
            pro_backburner_guard(),
            "HG_PRO_BACKBURNER=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pro_hardware_not_allowed_default",
            not pro_hardware_allowed(),
            "HG_PRO_HARDWARE_ALLOWED=0",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pro_static_fixtures_only_default",
            pro_static_fixtures_only(),
            "HG_PRO_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pro_refuse_stale_default",
            pro_refuse_stale_body_state(),
            "HG_PRO_REFUSE_STALE_BODY_STATE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pro_planning_spec_backburner",
            backburner["planning_spec_declares_backburner"],
            str(workspace / "docs/planning/proprioceptive_body_model/PRO_SPEC.md"),
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pro_embodiment_hardware_deferred",
            backburner["embodiment_hardware_deferred"],
            "backburner_guard_active and hardware_not_allowed",
        )
    )

    fences_ok, fence_detail = check_runtime_import_fences()
    checks.append(PolicyBatchCheck("runtime_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "pro_disabled_by_default",
            not pro_enabled(),
            "HG_PRO_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "pro",
        "feature": "PRO",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "backburner_boundary": backburner,
    }


__all__ = ["run_pro_closure_checks"]
