"""OBL closure checks for Batch S5-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    obl_enabled,
    obl_refuse_obligation_as_authority,
    obl_refuse_stale_obligation,
    obl_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.obligation_ledger.events import planned_obl_event_refs


def run_obl_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "obligation_ledger"
    checks.append(PolicyBatchCheck("obl_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "obligation_ledger_gate.py"
    checks.append(PolicyBatchCheck("obl_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "obl"
    checks.append(PolicyBatchCheck("obl_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "obligation_ledger" / "OBL_SPEC.md"
    checks.append(PolicyBatchCheck("obl_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_obl_event_refs()
    checks.append(
        PolicyBatchCheck(
            "obl_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "obl_static_fixtures_only_default",
            obl_static_fixtures_only(),
            "HG_OBL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "obl_refuse_stale_obligation_default",
            obl_refuse_stale_obligation(),
            "HG_OBL_REFUSE_STALE_OBLIGATION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "obl_refuse_obligation_as_authority_default",
            obl_refuse_obligation_as_authority(),
            "HG_OBL_REFUSE_OBLIGATION_AS_AUTHORITY=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "obl_disabled_by_default",
            not obl_enabled(),
            "HG_OBL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "obl",
        "feature": "OBL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_obl_closure_checks"]
