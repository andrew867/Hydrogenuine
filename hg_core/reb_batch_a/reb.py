"""REB closure checks for Batch REB-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.reb_cluster.batch_checks import reb_rtc_design_checks
from hg_core.reb_cluster.config import (
    reb_enabled,
    reb_fake_dispatch_only,
    reb_refuse_authority_conversion,
    reb_refuse_stale_reentry_request,
    reb_static_fixtures_only,
)
from hg_core.reb_cluster.events import planned_reb_event_refs
from hg_core.reb_cluster.no_authority import check_reb_import_fences


def run_reb_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "reentry_boundary"
    checks.append(PolicyBatchCheck("reb_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "reb_reentry_gate.py"
    checks.append(PolicyBatchCheck("reb_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "reb"
    checks.append(PolicyBatchCheck("reb_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "reentry_boundary" / "REB_SPEC.md"
    checks.append(PolicyBatchCheck("reb_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        reb_rtc_design_checks(
            prefix="reb",
            events=planned_reb_event_refs(),
            minimum_events=16,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "reb_static_fixtures_only_default",
            reb_static_fixtures_only(),
            "HG_REB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "reb_refuse_stale_reentry_request_default",
            reb_refuse_stale_reentry_request(),
            "HG_REB_REFUSE_STALE_REENTRY_REQUEST=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "reb_refuse_authority_conversion_default",
            reb_refuse_authority_conversion(),
            "HG_REB_REFUSE_AUTHORITY_CONVERSION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "reb_fake_dispatch_only_default",
            reb_fake_dispatch_only(),
            "HG_REB_FAKE_DISPATCH_ONLY=1",
        )
    )

    fences_ok, fence_detail = check_reb_import_fences()
    checks.append(
        PolicyBatchCheck("reb_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    fixtures = workspace / "hg_runtime" / "reentry_boundary" / "fixtures.py"
    checks.append(
        PolicyBatchCheck(
            "reb_static_fixture_bundles_present",
            fixtures.is_file(),
            str(fixtures.relative_to(workspace)),
        )
    )

    policies = workspace / "hg_runtime" / "reentry_boundary" / "policies.py"
    checks.append(
        PolicyBatchCheck(
            "reb_static_long_gap_policies_present",
            policies.is_file(),
            str(policies.relative_to(workspace)),
        )
    )

    classifier = workspace / "hg_runtime" / "reentry_boundary" / "classifier.py"
    checks.append(
        PolicyBatchCheck(
            "reb_static_long_gap_classifier_present",
            classifier.is_file(),
            str(classifier.relative_to(workspace)),
        )
    )

    audit_mod = workspace / "hg_runtime" / "reentry_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "reb_passive_audit_slice_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )

    queue_mod = workspace / "hg_runtime" / "reentry_boundary" / "queue.py"
    checks.append(
        PolicyBatchCheck(
            "reb_fake_queue_slice_present",
            queue_mod.is_file(),
            str(queue_mod.relative_to(workspace)),
        )
    )

    proposal_mod = workspace / "hg_runtime" / "reentry_boundary" / "proposal.py"
    checks.append(
        PolicyBatchCheck(
            "reb_fake_proposal_slice_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        )
    )

    checks.append(
        PolicyBatchCheck(
            "reb_disabled_by_default",
            not reb_enabled(),
            "HG_REB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "reb",
        "feature": "REB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_reb_audit_slice_checks(workspace: Path) -> dict[str, object]:
    audit_mod = workspace / "hg_runtime" / "reentry_boundary" / "audit.py"
    checks = [
        PolicyBatchCheck("reb_audit_module_present", audit_mod.is_file(), str(audit_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "reb_audit",
        "feature": "REB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_reb_queue_slice_checks(workspace: Path) -> dict[str, object]:
    queue_mod = workspace / "hg_runtime" / "reentry_boundary" / "queue.py"
    checks = [
        PolicyBatchCheck("reb_queue_module_present", queue_mod.is_file(), str(queue_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "reb_queue",
        "feature": "REB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_reb_proposal_slice_checks(workspace: Path) -> dict[str, object]:
    proposal_mod = workspace / "hg_runtime" / "reentry_boundary" / "proposal.py"
    checks = [
        PolicyBatchCheck(
            "reb_proposal_module_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "reb_fake_dispatch_only_default",
            reb_fake_dispatch_only(),
            "HG_REB_FAKE_DISPATCH_ONLY=1",
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "reb_proposal",
        "feature": "REB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_reb_audit_slice_checks",
    "run_reb_closure_checks",
    "run_reb_proposal_slice_checks",
    "run_reb_queue_slice_checks",
]
