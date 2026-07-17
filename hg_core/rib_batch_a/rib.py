"""RIB closure checks for Batch RIB-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.rib_cluster.batch_checks import rib_rtc_design_checks
from hg_core.rib_cluster.config import (
    rib_enabled,
    rib_fake_dispatch_only,
    rib_refuse_authority_conversion,
    rib_refuse_stale_spawn_request,
    rib_static_fixtures_only,
)
from hg_core.rib_cluster.events import planned_rib_event_refs
from hg_core.rib_cluster.no_authority import check_rib_import_fences


def run_rib_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "reproduction_inheritance_boundary"
    checks.append(PolicyBatchCheck("rib_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "rib_reproduction_inheritance_gate.py"
    checks.append(PolicyBatchCheck("rib_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "rib"
    checks.append(PolicyBatchCheck("rib_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "reproduction_inheritance_boundary" / "RIB_SPEC.md"
    checks.append(PolicyBatchCheck("rib_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        rib_rtc_design_checks(
            prefix="rib",
            events=planned_rib_event_refs(),
            minimum_events=12,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "rib_static_fixtures_only_default",
            rib_static_fixtures_only(),
            "HG_RIB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rib_refuse_stale_spawn_request_default",
            rib_refuse_stale_spawn_request(),
            "HG_RIB_REFUSE_STALE_SPAWN_REQUEST=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rib_refuse_authority_conversion_default",
            rib_refuse_authority_conversion(),
            "HG_RIB_REFUSE_AUTHORITY_CONVERSION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "rib_fake_dispatch_only_default",
            rib_fake_dispatch_only(),
            "HG_RIB_FAKE_DISPATCH_ONLY=1",
        )
    )

    fences_ok, fence_detail = check_rib_import_fences()
    checks.append(
        PolicyBatchCheck("rib_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    fixtures = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "fixtures.py"
    checks.append(
        PolicyBatchCheck(
            "rib_static_fixture_bundles_present",
            fixtures.is_file(),
            str(fixtures.relative_to(workspace)),
        )
    )

    policies = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "policies.py"
    checks.append(
        PolicyBatchCheck(
            "rib_static_inheritance_policies_present",
            policies.is_file(),
            str(policies.relative_to(workspace)),
        )
    )

    classifier = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "classifier.py"
    checks.append(
        PolicyBatchCheck(
            "rib_static_inheritance_classifier_present",
            classifier.is_file(),
            str(classifier.relative_to(workspace)),
        )
    )

    audit_mod = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "rib_passive_audit_slice_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )

    queue_mod = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "queue.py"
    checks.append(
        PolicyBatchCheck(
            "rib_fake_queue_slice_present",
            queue_mod.is_file(),
            str(queue_mod.relative_to(workspace)),
        )
    )

    proposal_mod = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "proposal.py"
    checks.append(
        PolicyBatchCheck(
            "rib_fake_proposal_slice_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        )
    )

    checks.append(
        PolicyBatchCheck(
            "rib_disabled_by_default",
            not rib_enabled(),
            "HG_RIB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rib",
        "feature": "RIB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_rib_audit_slice_checks(workspace: Path) -> dict[str, object]:
    audit_mod = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "audit.py"
    checks = [
        PolicyBatchCheck("rib_audit_module_present", audit_mod.is_file(), str(audit_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rib_audit",
        "feature": "RIB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_rib_queue_slice_checks(workspace: Path) -> dict[str, object]:
    queue_mod = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "queue.py"
    checks = [
        PolicyBatchCheck("rib_queue_module_present", queue_mod.is_file(), str(queue_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rib_queue",
        "feature": "RIB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_rib_proposal_slice_checks(workspace: Path) -> dict[str, object]:
    proposal_mod = workspace / "hg_runtime" / "reproduction_inheritance_boundary" / "proposal.py"
    checks = [
        PolicyBatchCheck(
            "rib_proposal_module_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "rib_fake_dispatch_only_default",
            rib_fake_dispatch_only(),
            "HG_RIB_FAKE_DISPATCH_ONLY=1",
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "rib_proposal",
        "feature": "RIB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_rib_audit_slice_checks",
    "run_rib_closure_checks",
    "run_rib_proposal_slice_checks",
    "run_rib_queue_slice_checks",
]
