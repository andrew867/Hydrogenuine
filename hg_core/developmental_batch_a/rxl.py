"""RXL closure checks for Batch D4-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.config import (
    rxl_enabled,
    rxl_refuse_expired_signal,
    rxl_static_fixtures_only,
)
from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.reciprocity_exchange.events import planned_rxl_event_refs


def run_rxl_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "reciprocity_exchange"
    checks.append(PolicyBatchCheck("rxl_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "rxl_reciprocity_exchange_gate.py"
    checks.append(PolicyBatchCheck("rxl_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "rxl"
    checks.append(PolicyBatchCheck("rxl_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "reciprocity_exchange_loop" / "RXL_SPEC.md"
    checks.append(PolicyBatchCheck("rxl_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_rxl_event_refs()
    checks.append(
        PolicyBatchCheck(
            "rxl_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "rxl_static_fixtures_only_default",
            rxl_static_fixtures_only(),
            "HG_RXL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rxl_refuse_expired_signal_default",
            rxl_refuse_expired_signal(),
            "HG_RXL_REFUSE_EXPIRED_SIGNAL=1",
        )
    )

    fences_ok, fence_detail = check_developmental_import_fences()
    checks.append(
        PolicyBatchCheck("developmental_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "rxl_disabled_by_default",
            not rxl_enabled(),
            "HG_RXL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rxl",
        "feature": "RXL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_rxl_closure_checks"]
