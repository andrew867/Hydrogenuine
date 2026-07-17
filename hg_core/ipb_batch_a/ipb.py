"""IPB closure checks for Batch IPB-A — full slice scope."""

from __future__ import annotations

from pathlib import Path

from hg_core.ipb_cluster.batch_checks import ipb_rtc_design_checks
from hg_core.ipb_cluster.config import (
    ipb_enabled,
    ipb_fake_dispatch_only,
    ipb_refuse_authority_conversion,
    ipb_refuse_stale_envelope,
    ipb_static_fixtures_only,
)
from hg_core.ipb_cluster.no_authority import check_ipb_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.internal_power_boundary.events import planned_ipb_event_refs


def _common_checks(workspace: Path, *, slice: str) -> list[PolicyBatchCheck]:
    module = workspace / "hg_runtime" / "internal_power_boundary"
    checks = [
        PolicyBatchCheck("ipb_module_present", module.is_dir(), str(module.relative_to(workspace))),
        PolicyBatchCheck(
            "ipb_gate_present",
            (workspace / "scripts" / "evals" / "ipb_internal_power_gate.py").is_file(),
            "scripts/evals/ipb_internal_power_gate.py",
        ),
        PolicyBatchCheck(
            "ipb_spec_present",
            (workspace / "docs" / "planning" / "internal_power_boundary" / "IPB_SPEC.md").is_file(),
            "docs/planning/internal_power_boundary/IPB_SPEC.md",
        ),
    ]
    if slice == "ipb":
        tests = workspace / "tests" / "ipb"
        checks.append(
            PolicyBatchCheck("ipb_tests_present", tests.is_dir(), str(tests.relative_to(workspace)))
        )
        checks.extend(
            ipb_rtc_design_checks(
                prefix="ipb",
                events=planned_ipb_event_refs(),
                minimum_events=16,
            )
        )
        checks.extend(
            [
                PolicyBatchCheck(
                    "ipb_static_fixtures_only_default",
                    ipb_static_fixtures_only(),
                    "HG_IPB_STATIC_FIXTURES_ONLY=1",
                ),
                PolicyBatchCheck(
                    "ipb_refuse_stale_envelope_default",
                    ipb_refuse_stale_envelope(),
                    "HG_IPB_REFUSE_STALE_ENVELOPE=1",
                ),
                PolicyBatchCheck(
                    "ipb_refuse_authority_conversion_default",
                    ipb_refuse_authority_conversion(),
                    "HG_IPB_REFUSE_AUTHORITY_CONVERSION=1",
                ),
            ]
        )
        fences_ok, fence_detail = check_ipb_import_fences()
        checks.append(
            PolicyBatchCheck(
                "ipb_import_fences",
                fences_ok,
                str(fence_detail) if not fences_ok else "clean",
            )
        )
        fixtures = module / "fixtures.py"
        checks.append(
            PolicyBatchCheck(
                "ipb_static_fixture_logs_present",
                fixtures.is_file(),
                str(fixtures.relative_to(workspace)),
            )
        )
        checks.append(
            PolicyBatchCheck(
                "ipb_disabled_by_default",
                not ipb_enabled(),
                "HG_IPB_ENABLED=0 default",
                critical=False,
            )
        )
    return checks


def _finalize(slice: str, checks: list[PolicyBatchCheck]) -> dict[str, object]:
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": slice,
        "feature": "IPB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_ipb_closure_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ipb")
    audit_mod = workspace / "hg_runtime" / "internal_power_boundary" / "audit.py"
    advisory_mod = workspace / "hg_runtime" / "internal_power_boundary" / "advisory.py"
    proposal_mod = workspace / "hg_runtime" / "internal_power_boundary" / "proposal.py"
    neighbor_mod = workspace / "hg_runtime" / "internal_power_boundary" / "neighbor_integration.py"
    checks.extend(
        [
            PolicyBatchCheck(
                "ipb_passive_audit_slice_present",
                audit_mod.is_file(),
                str(audit_mod.relative_to(workspace)),
            ),
            PolicyBatchCheck(
                "ipb_advisory_slice_present",
                advisory_mod.is_file(),
                str(advisory_mod.relative_to(workspace)),
            ),
            PolicyBatchCheck(
                "ipb_fake_proposal_slice_present",
                proposal_mod.is_file(),
                str(proposal_mod.relative_to(workspace)),
            ),
            PolicyBatchCheck(
                "ipb_neighbor_integration_slice_present",
                neighbor_mod.is_file(),
                str(neighbor_mod.relative_to(workspace)),
            ),
        ]
    )
    return _finalize("ipb", checks)


def run_ipb_audit_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ipb_audit")
    audit_mod = workspace / "hg_runtime" / "internal_power_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "ipb_audit_module_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )
    return _finalize("ipb_audit", checks)


def run_ipb_advisory_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ipb_advisory")
    advisory_mod = workspace / "hg_runtime" / "internal_power_boundary" / "advisory.py"
    checks.append(
        PolicyBatchCheck(
            "ipb_advisory_module_present",
            advisory_mod.is_file(),
            str(advisory_mod.relative_to(workspace)),
        )
    )
    return _finalize("ipb_advisory", checks)


def run_ipb_policy_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ipb_policy")
    proposal_mod = workspace / "hg_runtime" / "internal_power_boundary" / "proposal.py"
    checks.extend(
        [
            PolicyBatchCheck(
                "ipb_policy_module_present",
                proposal_mod.is_file(),
                str(proposal_mod.relative_to(workspace)),
            ),
            PolicyBatchCheck(
                "ipb_fake_dispatch_only_default",
                ipb_fake_dispatch_only(),
                "HG_IPB_FAKE_DISPATCH_ONLY=1",
            ),
        ]
    )
    return _finalize("ipb_policy", checks)


def run_ipb_extras_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ipb_extras")
    neighbor_mod = workspace / "hg_runtime" / "internal_power_boundary" / "neighbor_integration.py"
    checks.append(
        PolicyBatchCheck(
            "ipb_neighbor_integration_module_present",
            neighbor_mod.is_file(),
            str(neighbor_mod.relative_to(workspace)),
        )
    )
    return _finalize("ipb_extras", checks)


__all__ = [
    "run_ipb_advisory_slice_checks",
    "run_ipb_audit_slice_checks",
    "run_ipb_closure_checks",
    "run_ipb_extras_slice_checks",
    "run_ipb_policy_slice_checks",
]
