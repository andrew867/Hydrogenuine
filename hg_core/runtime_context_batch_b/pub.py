"""PUB slice closure checks for Batch R2-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.runtime_context.config import pub_enabled, pub_require_evidence_for_public
from hg_runtime.publication_disclosure_boundary.events import planned_rtc_events


def run_pub_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "publication_disclosure_boundary"
    checks.append(PolicyBatchCheck("pub_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "publication_disclosure_boundary_gate.py"
    checks.append(PolicyBatchCheck("pub_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "publication_disclosure_boundary"
    checks.append(PolicyBatchCheck("pub_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    events = planned_rtc_events()
    checks.append(
        PolicyBatchCheck(
            "pub_rtc_event_design_present",
            len(events) >= 8,
            f"planned_events={len(events)}",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pub_rtc_events_no_authority_fields",
            all(not e.get("authority_fields") for e in events),
            "all events authority_fields=False",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "pub_require_evidence_for_public_default",
            pub_require_evidence_for_public(),
            "HG_PUB_REQUIRE_EVIDENCE_FOR_PUBLIC=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "pub_disabled_by_default",
            not pub_enabled(),
            "HG_PUB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "pub",
        "feature": "PUB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_pub_closure_checks"]
