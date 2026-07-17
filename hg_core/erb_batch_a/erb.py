"""ERB closure checks for Batch ERB-A — full slice scope."""

from __future__ import annotations

from pathlib import Path

from hg_core.erb_cluster.batch_checks import erb_rtc_design_checks
from hg_core.erb_cluster.config import (
    erb_enabled,
    erb_refuse_authority_conversion,
    erb_refuse_stale_policy,
    erb_static_fixtures_only,
)
from hg_core.erb_cluster.no_authority import check_erb_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.external_relation_boundary.events import planned_erb_event_refs


def _common_checks(workspace: Path, *, slice: str) -> list[PolicyBatchCheck]:
    module = workspace / "hg_runtime" / "external_relation_boundary"
    checks = [
        PolicyBatchCheck("erb_module_present", module.is_dir(), str(module.relative_to(workspace))),
        PolicyBatchCheck(
            "erb_gate_present",
            (workspace / "scripts" / "evals" / "erb_external_relation_gate.py").is_file(),
            "scripts/evals/erb_external_relation_gate.py",
        ),
        PolicyBatchCheck(
            "erb_spec_present",
            (workspace / "docs" / "planning" / "external_relation_boundary" / "ERB_SPEC.md").is_file(),
            "docs/planning/external_relation_boundary/ERB_SPEC.md",
        ),
    ]
    if slice == "erb":
        checks.extend(
            erb_rtc_design_checks(
                prefix="erb",
                events=planned_erb_event_refs(),
                minimum_events=12,
            )
        )
        checks.extend(
            [
                PolicyBatchCheck(
                    "erb_static_fixtures_only_default",
                    erb_static_fixtures_only(),
                    "HG_ERB_STATIC_FIXTURES_ONLY=1",
                ),
                PolicyBatchCheck(
                    "erb_refuse_stale_policy_default",
                    erb_refuse_stale_policy(),
                    "HG_ERB_REFUSE_STALE_POLICY=1",
                ),
                PolicyBatchCheck(
                    "erb_refuse_authority_conversion_default",
                    erb_refuse_authority_conversion(),
                    "HG_ERB_REFUSE_AUTHORITY_CONVERSION=1",
                ),
            ]
        )
        fences_ok, fence_detail = check_erb_import_fences()
        checks.append(
            PolicyBatchCheck(
                "erb_import_fences",
                fences_ok,
                str(fence_detail) if not fences_ok else "clean",
            )
        )
        fixtures = module / "fixtures.py"
        checks.append(
            PolicyBatchCheck(
                "erb_static_fixture_bundles_present",
                fixtures.is_file(),
                str(fixtures.relative_to(workspace)),
            )
        )
        policies = module / "policies.py"
        checks.append(
            PolicyBatchCheck(
                "erb_static_routing_policies_present",
                policies.is_file(),
                str(policies.relative_to(workspace)),
            )
        )
        audit_mod = module / "audit.py"
        checks.append(
            PolicyBatchCheck(
                "erb_passive_audit_slice_present",
                audit_mod.is_file(),
                str(audit_mod.relative_to(workspace)),
            )
        )
        digest_mod = module / "digest.py"
        checks.append(
            PolicyBatchCheck(
                "erb_disclosure_digest_slice_present",
                digest_mod.is_file(),
                str(digest_mod.relative_to(workspace)),
            )
        )
        integration_mod = module / "integration.py"
        checks.append(
            PolicyBatchCheck(
                "erb_cluster_integration_slice_present",
                integration_mod.is_file(),
                str(integration_mod.relative_to(workspace)),
            )
        )
        checks.append(
            PolicyBatchCheck(
                "erb_disabled_by_default",
                not erb_enabled(),
                "HG_ERB_ENABLED=0 default",
                critical=False,
            )
        )
    return checks


def _finalize(slice: str, checks: list[PolicyBatchCheck]) -> dict[str, object]:
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": slice,
        "feature": "ERB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_erb_closure_checks(workspace: Path) -> dict[str, object]:
    return _finalize("erb", _common_checks(workspace, slice="erb"))


def run_erb_audit_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="erb_audit")
    audit_mod = workspace / "hg_runtime" / "external_relation_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "erb_audit_module_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )
    return _finalize("erb_audit", checks)


def run_erb_digest_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="erb_digest")
    digest_mod = workspace / "hg_runtime" / "external_relation_boundary" / "digest.py"
    checks.append(
        PolicyBatchCheck(
            "erb_digest_module_present",
            digest_mod.is_file(),
            str(digest_mod.relative_to(workspace)),
        )
    )
    return _finalize("erb_digest", checks)


def run_erb_integration_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="erb_integration")
    integration_mod = workspace / "hg_runtime" / "external_relation_boundary" / "integration.py"
    checks.append(
        PolicyBatchCheck(
            "erb_integration_module_present",
            integration_mod.is_file(),
            str(integration_mod.relative_to(workspace)),
        )
    )
    return _finalize("erb_integration", checks)


__all__ = [
    "run_erb_audit_slice_checks",
    "run_erb_closure_checks",
    "run_erb_digest_slice_checks",
    "run_erb_integration_slice_checks",
]
