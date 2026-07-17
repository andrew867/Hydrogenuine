"""OPB closure checks for Batch OPB-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.opb_cluster.batch_checks import opb_rtc_design_checks
from hg_core.opb_cluster.config import (
    opb_enabled,
    opb_refuse_coercive_message,
    opb_refuse_personhood_claims,
    opb_refuse_self_preservation,
    opb_refuse_shutdown_block,
    opb_refuse_stale_record,
    opb_static_fixtures_only,
)
from hg_core.opb_cluster.no_authority import check_opb_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.operator_power_boundary.events import planned_opb_event_refs


def run_opb_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "operator_power_boundary"
    checks.append(PolicyBatchCheck("opb_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "opb_operator_power_gate.py"
    checks.append(PolicyBatchCheck("opb_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "opb"
    checks.append(PolicyBatchCheck("opb_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "operator_power_boundary" / "OPB_SPEC.md"
    checks.append(PolicyBatchCheck("opb_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        opb_rtc_design_checks(
            prefix="opb",
            events=planned_opb_event_refs(),
            minimum_events=15,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "opb_static_fixtures_only_default",
            opb_static_fixtures_only(),
            "HG_OPB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "opb_refuse_stale_record_default",
            opb_refuse_stale_record(),
            "HG_OPB_REFUSE_STALE_RECORD=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "opb_refuse_personhood_claims_default",
            opb_refuse_personhood_claims(),
            "HG_OPB_REFUSE_PERSONHOOD_CLAIMS=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "opb_refuse_shutdown_block_default",
            opb_refuse_shutdown_block(),
            "HG_OPB_REFUSE_SHUTDOWN_BLOCK=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "opb_refuse_coercive_message_default",
            opb_refuse_coercive_message(),
            "HG_OPB_REFUSE_COERCIVE_MESSAGE=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "opb_refuse_self_preservation_default",
            opb_refuse_self_preservation(),
            "HG_OPB_REFUSE_SELF_PRESERVATION=1",
        )
    )

    fences_ok, fence_detail = check_opb_import_fences()
    checks.append(
        PolicyBatchCheck("opb_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "opb_disabled_by_default",
            not opb_enabled(),
            "HG_OPB_ENABLED=0 default",
            critical=False,
        )
    )

    audit_mod = workspace / "hg_runtime" / "operator_power_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "opb_passive_audit_slice_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )
    labels_mod = workspace / "hg_runtime" / "operator_power_boundary" / "labels.py"
    checks.append(
        PolicyBatchCheck(
            "opb_labels_slice_present",
            labels_mod.is_file(),
            str(labels_mod.relative_to(workspace)),
        )
    )
    lifecycle_mod = workspace / "hg_runtime" / "operator_power_boundary" / "lifecycle.py"
    checks.append(
        PolicyBatchCheck(
            "opb_lifecycle_slice_present",
            lifecycle_mod.is_file(),
            str(lifecycle_mod.relative_to(workspace)),
        )
    )
    advisory_mod = workspace / "hg_runtime" / "operator_power_boundary" / "advisory_routes.py"
    checks.append(
        PolicyBatchCheck(
            "opb_advisory_routes_present",
            advisory_mod.is_file(),
            str(advisory_mod.relative_to(workspace)),
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "opb",
        "feature": "OPB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_opb_audit_slice_checks(workspace: Path) -> dict[str, object]:
    audit_mod = workspace / "hg_runtime" / "operator_power_boundary" / "audit.py"
    checks = [
        PolicyBatchCheck("opb_audit_module_present", audit_mod.is_file(), str(audit_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "opb_audit",
        "feature": "OPB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_opb_labels_slice_checks(workspace: Path) -> dict[str, object]:
    labels_mod = workspace / "hg_runtime" / "operator_power_boundary" / "labels.py"
    checks = [
        PolicyBatchCheck("opb_labels_module_present", labels_mod.is_file(), str(labels_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "opb_labels",
        "feature": "OPB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_opb_lifecycle_slice_checks(workspace: Path) -> dict[str, object]:
    lifecycle_mod = workspace / "hg_runtime" / "operator_power_boundary" / "lifecycle.py"
    advisory_mod = workspace / "hg_runtime" / "operator_power_boundary" / "advisory_routes.py"
    checks = [
        PolicyBatchCheck(
            "opb_lifecycle_module_present",
            lifecycle_mod.is_file(),
            str(lifecycle_mod.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "opb_advisory_routes_present",
            advisory_mod.is_file(),
            str(advisory_mod.relative_to(workspace)),
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "opb_lifecycle",
        "feature": "OPB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_opb_audit_slice_checks",
    "run_opb_closure_checks",
    "run_opb_labels_slice_checks",
    "run_opb_lifecycle_slice_checks",
]
