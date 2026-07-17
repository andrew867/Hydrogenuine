"""BCP slice closure checks for Batch R2-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import bcp_enabled, bcp_refuse_stale_packet
from hg_core.runtime_context.no_authority import check_runtime_import_fences
from hg_runtime.bootstrap_context_packet.events import planned_rtc_events


def run_bcp_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "bootstrap_context_packet"
    checks.append(PolicyBatchCheck("bcp_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "bootstrap_context_packet_gate.py"
    checks.append(PolicyBatchCheck("bcp_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "bootstrap_context_packet"
    checks.append(PolicyBatchCheck("bcp_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    events = planned_rtc_events()
    checks.append(
        PolicyBatchCheck(
            "bcp_rtc_event_design_present",
            len(events) >= 9,
            f"planned_events={len(events)}",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "bcp_rtc_events_no_authority_fields",
            all(not e.get("authority_fields") for e in events),
            "all events authority_fields=False",
        )
    )

    fences_ok, fence_detail = check_runtime_import_fences()
    checks.append(PolicyBatchCheck("runtime_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean"))

    checks.append(
        PolicyBatchCheck(
            "bcp_refuse_stale_default",
            bcp_refuse_stale_packet(),
            "HG_BCP_REFUSE_STALE_PACKET=1",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "bcp_disabled_by_default",
            not bcp_enabled(),
            "HG_BCP_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "bcp",
        "feature": "BCP",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_bcp_closure_checks"]
