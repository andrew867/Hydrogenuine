"""P7 closure checks for Batch P7-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.exciton_cluster.batch_checks import exciton_rtc_design_checks
from hg_core.exciton_cluster.config import (
    exciton_backburner_guard,
    exciton_enabled,
    exciton_fake_dispatch_only,
    exciton_native_ui_allowed,
    exciton_refuse_authority_conversion,
    exciton_refuse_stale_approval,
    exciton_static_fixtures_only,
)
from hg_core.exciton_cluster.events import planned_exciton_event_refs
from hg_core.exciton_cluster.no_authority import check_exciton_import_fences


def run_exciton_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "operator_product_surface"
    checks.append(PolicyBatchCheck("exciton_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "exciton_operator_surface_gate.py"
    checks.append(PolicyBatchCheck("exciton_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "operator_product_surface"
    checks.append(PolicyBatchCheck("exciton_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "operator_product_surface" / "OPS_SPEC.md"
    checks.append(PolicyBatchCheck("ops_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        exciton_rtc_design_checks(
            prefix="exciton",
            events=planned_exciton_event_refs(),
            minimum_events=14,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "exciton_static_fixtures_only_default",
            exciton_static_fixtures_only(),
            "HG_EXCITON_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "exciton_refuse_stale_approval_default",
            exciton_refuse_stale_approval(),
            "HG_EXCITON_REFUSE_STALE_APPROVAL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "exciton_refuse_authority_conversion_default",
            exciton_refuse_authority_conversion(),
            "HG_EXCITON_REFUSE_AUTHORITY_CONVERSION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "exciton_fake_dispatch_only_default",
            exciton_fake_dispatch_only(),
            "HG_EXCITON_FAKE_DISPATCH_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "exciton_backburner_guard_default",
            exciton_backburner_guard(),
            "HG_EXCITON_BACKBURNER=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "exciton_native_ui_not_allowed_default",
            not exciton_native_ui_allowed(),
            "HG_EXCITON_NATIVE_UI_ALLOWED=0",
        )
    )

    fences_ok, fence_detail = check_exciton_import_fences()
    checks.append(
        PolicyBatchCheck("exciton_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    fixtures = workspace / "hg_runtime" / "operator_product_surface" / "fixtures.py"
    checks.append(
        PolicyBatchCheck(
            "exciton_static_fixture_bundles_present",
            fixtures.is_file(),
            str(fixtures.relative_to(workspace)),
        )
    )

    classifier = workspace / "hg_runtime" / "operator_product_surface" / "classifier.py"
    checks.append(
        PolicyBatchCheck(
            "exciton_polish_classifier_present",
            classifier.is_file(),
            str(classifier.relative_to(workspace)),
        )
    )

    audit_mod = workspace / "hg_runtime" / "operator_product_surface" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "exciton_passive_audit_slice_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )

    queue_mod = workspace / "hg_runtime" / "operator_product_surface" / "queue.py"
    checks.append(
        PolicyBatchCheck(
            "exciton_fake_queue_slice_present",
            queue_mod.is_file(),
            str(queue_mod.relative_to(workspace)),
        )
    )

    proposal_mod = workspace / "hg_runtime" / "operator_product_surface" / "proposal.py"
    checks.append(
        PolicyBatchCheck(
            "exciton_fake_proposal_slice_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        )
    )

    backburner = workspace / "hg_runtime" / "operator_product_surface" / "backburner.py"
    checks.append(
        PolicyBatchCheck(
            "exciton_backburner_guard_present",
            backburner.is_file(),
            str(backburner.relative_to(workspace)),
        )
    )

    checks.append(
        PolicyBatchCheck(
            "exciton_disabled_by_default",
            not exciton_enabled(),
            "HG_EXCITON_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "exciton",
        "feature": "EXCITON",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_exciton_audit_slice_checks(workspace: Path) -> dict[str, object]:
    audit_mod = workspace / "hg_runtime" / "operator_product_surface" / "audit.py"
    checks = [
        PolicyBatchCheck("exciton_audit_module_present", audit_mod.is_file(), str(audit_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "exciton_audit",
        "feature": "EXCITON",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_exciton_queue_slice_checks(workspace: Path) -> dict[str, object]:
    queue_mod = workspace / "hg_runtime" / "operator_product_surface" / "queue.py"
    checks = [
        PolicyBatchCheck("exciton_queue_module_present", queue_mod.is_file(), str(queue_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "exciton_queue",
        "feature": "EXCITON",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_exciton_proposal_slice_checks(workspace: Path) -> dict[str, object]:
    proposal_mod = workspace / "hg_runtime" / "operator_product_surface" / "proposal.py"
    checks = [
        PolicyBatchCheck(
            "exciton_proposal_module_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "exciton_fake_dispatch_only_default",
            exciton_fake_dispatch_only(),
            "HG_EXCITON_FAKE_DISPATCH_ONLY=1",
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "exciton_proposal",
        "feature": "EXCITON",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_plt_slice_checks(workspace: Path) -> dict[str, object]:
    plt_mod = workspace / "hg_runtime" / "operator_product_surface" / "plt.py"
    checks = [
        PolicyBatchCheck("plt_polish_module_present", plt_mod.is_file(), str(plt_mod.relative_to(workspace))),
        PolicyBatchCheck(
            "plt_after_pres_trb_sil_note",
            True,
            "PLT polish descriptors require pres_trb_sil_boundaries_stable in exciton fixtures",
            critical=False,
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "plt",
        "feature": "PLT",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_exciton_audit_slice_checks",
    "run_exciton_closure_checks",
    "run_exciton_proposal_slice_checks",
    "run_exciton_queue_slice_checks",
    "run_plt_slice_checks",
]
