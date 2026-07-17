"""P7-B closure checks for Batch P7-B."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.embodiment_oea_cluster.batch_checks import eog_rtc_design_checks
from hg_core.embodiment_oea_cluster.config import (
    eog_backburner_guard,
    eog_enabled,
    eog_fake_dispatch_only,
    eog_hardware_allowed,
    eog_refuse_authority_conversion,
    eog_refuse_stale_approval,
    eog_static_fixtures_only,
)
from hg_core.embodiment_oea_cluster.events import planned_eog_event_refs
from hg_core.embodiment_oea_cluster.no_authority import check_eog_import_fences


def run_embodiment_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "embodiment_oea_growth"
    checks.append(PolicyBatchCheck("eog_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "embodiment_oea_growth_gate.py"
    checks.append(PolicyBatchCheck("eog_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "embodiment_oea_growth"
    checks.append(PolicyBatchCheck("eog_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "embodiment_oea_growth" / "EOG_SPEC.md"
    checks.append(PolicyBatchCheck("eog_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    pro_bridge = workspace / "hg_runtime" / "embodiment_oea_growth" / "pro_bridge.py"
    checks.append(
        PolicyBatchCheck(
            "eog_pro_bridge_present",
            pro_bridge.is_file(),
            str(pro_bridge.relative_to(workspace)),
        )
    )

    checks.extend(
        eog_rtc_design_checks(
            prefix="eog",
            events=planned_eog_event_refs(),
            minimum_events=14,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "eog_static_fixtures_only_default",
            eog_static_fixtures_only(),
            "HG_EOG_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "eog_refuse_stale_approval_default",
            eog_refuse_stale_approval(),
            "HG_EOG_REFUSE_STALE_APPROVAL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "eog_refuse_authority_conversion_default",
            eog_refuse_authority_conversion(),
            "HG_EOG_REFUSE_AUTHORITY_CONVERSION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "eog_fake_dispatch_only_default",
            eog_fake_dispatch_only(),
            "HG_EOG_FAKE_DISPATCH_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "eog_backburner_guard_default",
            eog_backburner_guard(),
            "HG_EOG_BACKBURNER=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "eog_hardware_not_allowed_default",
            not eog_hardware_allowed(),
            "HG_EOG_HARDWARE_ALLOWED=0",
        )
    )

    fences_ok, fence_detail = check_eog_import_fences()
    checks.append(
        PolicyBatchCheck("eog_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    for rel in (
        "fixtures.py",
        "classifier.py",
        "audit.py",
        "queue.py",
        "proposal.py",
        "backburner.py",
        "oea_growth.py",
    ):
        path = module / rel
        checks.append(
            PolicyBatchCheck(
                f"eog_{rel.replace('.py', '')}_present",
                path.is_file(),
                str(path.relative_to(workspace)),
            )
        )

    checks.append(
        PolicyBatchCheck(
            "eog_disabled_by_default",
            not eog_enabled(),
            "HG_EOG_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "embodiment",
        "feature": "EOG",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_embodiment_audit_slice_checks(workspace: Path) -> dict[str, object]:
    audit_mod = workspace / "hg_runtime" / "embodiment_oea_growth" / "audit.py"
    checks = [
        PolicyBatchCheck("eog_audit_module_present", audit_mod.is_file(), str(audit_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "embodiment_audit",
        "feature": "EOG",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_embodiment_queue_slice_checks(workspace: Path) -> dict[str, object]:
    queue_mod = workspace / "hg_runtime" / "embodiment_oea_growth" / "queue.py"
    checks = [
        PolicyBatchCheck("eog_queue_module_present", queue_mod.is_file(), str(queue_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "embodiment_queue",
        "feature": "EOG",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_embodiment_proposal_slice_checks(workspace: Path) -> dict[str, object]:
    proposal_mod = workspace / "hg_runtime" / "embodiment_oea_growth" / "proposal.py"
    checks = [
        PolicyBatchCheck(
            "eog_proposal_module_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "eog_fake_dispatch_only_default",
            eog_fake_dispatch_only(),
            "HG_EOG_FAKE_DISPATCH_ONLY=1",
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "embodiment_proposal",
        "feature": "EOG",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_oea_growth_slice_checks(workspace: Path) -> dict[str, object]:
    oea_mod = workspace / "hg_runtime" / "embodiment_oea_growth" / "oea_growth.py"
    checks = [
        PolicyBatchCheck("oea_growth_module_present", oea_mod.is_file(), str(oea_mod.relative_to(workspace))),
        PolicyBatchCheck(
            "oea_catalog_bounded_note",
            True,
            "OEA catalog entries require bounded_by_gpp_ueak and soar_review_required",
            critical=False,
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "oea_growth",
        "feature": "OEA",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_embodiment_audit_slice_checks",
    "run_embodiment_closure_checks",
    "run_embodiment_proposal_slice_checks",
    "run_embodiment_queue_slice_checks",
    "run_oea_growth_slice_checks",
]
