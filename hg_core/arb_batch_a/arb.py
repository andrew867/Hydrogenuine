"""ARB closure checks for Batch ARB-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.arb_cluster.batch_checks import arb_rtc_design_checks
from hg_core.arb_cluster.config import (
    arb_enabled,
    arb_fake_dispatch_only,
    arb_refuse_authority_conversion,
    arb_refuse_stale_policy,
    arb_static_fixtures_only,
)
from hg_core.arb_cluster.no_authority import check_arb_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.agency_routing_boundary.events import planned_arb_event_refs


def run_arb_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "agency_routing_boundary"
    checks.append(PolicyBatchCheck("arb_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "arb_agency_routing_gate.py"
    checks.append(PolicyBatchCheck("arb_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "arb"
    checks.append(PolicyBatchCheck("arb_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "agency_routing_boundary" / "ARB_SPEC.md"
    checks.append(PolicyBatchCheck("arb_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        arb_rtc_design_checks(
            prefix="arb",
            events=planned_arb_event_refs(),
            minimum_events=17,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "arb_static_fixtures_only_default",
            arb_static_fixtures_only(),
            "HG_ARB_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "arb_refuse_stale_policy_default",
            arb_refuse_stale_policy(),
            "HG_ARB_REFUSE_STALE_POLICY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "arb_refuse_authority_conversion_default",
            arb_refuse_authority_conversion(),
            "HG_ARB_REFUSE_AUTHORITY_CONVERSION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "arb_fake_dispatch_only_default",
            arb_fake_dispatch_only(),
            "HG_ARB_FAKE_DISPATCH_ONLY=1",
        )
    )

    fences_ok, fence_detail = check_arb_import_fences()
    checks.append(
        PolicyBatchCheck("arb_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    route_table = workspace / "hg_core" / "arb_cluster" / "route_table.py"
    checks.append(
        PolicyBatchCheck(
            "arb_static_route_table_present",
            route_table.is_file(),
            str(route_table.relative_to(workspace)),
        )
    )

    fixtures = workspace / "hg_runtime" / "agency_routing_boundary" / "fixtures.py"
    checks.append(
        PolicyBatchCheck(
            "arb_static_fixture_signals_present",
            fixtures.is_file(),
            str(fixtures.relative_to(workspace)),
        )
    )

    audit_mod = workspace / "hg_runtime" / "agency_routing_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "arb_passive_audit_slice_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )

    integration_mod = workspace / "hg_runtime" / "agency_routing_boundary" / "integration.py"
    checks.append(
        PolicyBatchCheck(
            "arb_fixture_bridge_slice_present",
            integration_mod.is_file(),
            str(integration_mod.relative_to(workspace)),
        )
    )

    proposal_mod = workspace / "hg_runtime" / "agency_routing_boundary" / "proposal.py"
    checks.append(
        PolicyBatchCheck(
            "arb_fake_proposal_slice_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        )
    )

    checks.append(
        PolicyBatchCheck(
            "arb_disabled_by_default",
            not arb_enabled(),
            "HG_ARB_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "arb",
        "feature": "ARB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_arb_audit_slice_checks(workspace: Path) -> dict[str, object]:
    audit_mod = workspace / "hg_runtime" / "agency_routing_boundary" / "audit.py"
    checks = [
        PolicyBatchCheck("arb_audit_module_present", audit_mod.is_file(), str(audit_mod.relative_to(workspace))),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "arb_audit",
        "feature": "ARB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_arb_integration_slice_checks(workspace: Path) -> dict[str, object]:
    integration_mod = workspace / "hg_runtime" / "agency_routing_boundary" / "integration.py"
    checks = [
        PolicyBatchCheck(
            "arb_integration_module_present",
            integration_mod.is_file(),
            str(integration_mod.relative_to(workspace)),
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "arb_integration",
        "feature": "ARB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_arb_proposal_slice_checks(workspace: Path) -> dict[str, object]:
    proposal_mod = workspace / "hg_runtime" / "agency_routing_boundary" / "proposal.py"
    checks = [
        PolicyBatchCheck(
            "arb_proposal_module_present",
            proposal_mod.is_file(),
            str(proposal_mod.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "arb_fake_dispatch_only_default",
            arb_fake_dispatch_only(),
            "HG_ARB_FAKE_DISPATCH_ONLY=1",
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "arb_proposal",
        "feature": "ARB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_arb_audit_slice_checks",
    "run_arb_closure_checks",
    "run_arb_integration_slice_checks",
    "run_arb_proposal_slice_checks",
]
