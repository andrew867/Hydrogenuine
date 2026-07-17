"""IMB closure checks for Batch IMB-A — full slice scope."""

from __future__ import annotations

from pathlib import Path

from hg_core.imb_cluster.batch_checks import imb_rtc_design_checks
from hg_core.imb_cluster.config import (
    imb_enabled,
    imb_refuse_authority_conversion,
    imb_refuse_stale_policy,
    imb_static_fixtures_only,
)
from hg_core.imb_cluster.no_authority import check_imb_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.internal_mediation_boundary.events import planned_imb_event_refs


def _common_checks(workspace: Path, *, slice: str) -> list[PolicyBatchCheck]:
    module = workspace / "hg_runtime" / "internal_mediation_boundary"
    checks = [
        PolicyBatchCheck("imb_module_present", module.is_dir(), str(module.relative_to(workspace))),
        PolicyBatchCheck(
            "imb_gate_present",
            (workspace / "scripts" / "evals" / "imb_internal_mediation_gate.py").is_file(),
            "scripts/evals/imb_internal_mediation_gate.py",
        ),
        PolicyBatchCheck(
            "imb_spec_present",
            (workspace / "docs" / "planning" / "internal_mediation_boundary" / "IMB_SPEC.md").is_file(),
            "docs/planning/internal_mediation_boundary/IMB_SPEC.md",
        ),
    ]
    if slice == "imb":
        checks.extend(
            imb_rtc_design_checks(
                prefix="imb",
                events=planned_imb_event_refs(),
                minimum_events=12,
            )
        )
        checks.extend(
            [
                PolicyBatchCheck(
                    "imb_static_fixtures_only_default",
                    imb_static_fixtures_only(),
                    "HG_IMB_STATIC_FIXTURES_ONLY=1",
                ),
                PolicyBatchCheck(
                    "imb_refuse_stale_policy_default",
                    imb_refuse_stale_policy(),
                    "HG_IMB_REFUSE_STALE_POLICY=1",
                ),
                PolicyBatchCheck(
                    "imb_refuse_authority_conversion_default",
                    imb_refuse_authority_conversion(),
                    "HG_IMB_REFUSE_AUTHORITY_CONVERSION=1",
                ),
            ]
        )
        fences_ok, fence_detail = check_imb_import_fences()
        checks.append(
            PolicyBatchCheck(
                "imb_import_fences",
                fences_ok,
                str(fence_detail) if not fences_ok else "clean",
            )
        )
        fixtures = module / "fixtures.py"
        checks.append(
            PolicyBatchCheck(
                "imb_static_fixture_bundles_present",
                fixtures.is_file(),
                str(fixtures.relative_to(workspace)),
            )
        )
        policies = module / "policies.py"
        checks.append(
            PolicyBatchCheck(
                "imb_static_mediation_policies_present",
                policies.is_file(),
                str(policies.relative_to(workspace)),
            )
        )
        audit_mod = module / "audit.py"
        checks.append(
            PolicyBatchCheck(
                "imb_passive_audit_slice_present",
                audit_mod.is_file(),
                str(audit_mod.relative_to(workspace)),
            )
        )
        digest_mod = module / "digest.py"
        checks.append(
            PolicyBatchCheck(
                "imb_mediation_digest_slice_present",
                digest_mod.is_file(),
                str(digest_mod.relative_to(workspace)),
            )
        )
        integration_mod = module / "integration.py"
        checks.append(
            PolicyBatchCheck(
                "imb_cluster_integration_slice_present",
                integration_mod.is_file(),
                str(integration_mod.relative_to(workspace)),
            )
        )
        checks.append(
            PolicyBatchCheck(
                "imb_disabled_by_default",
                not imb_enabled(),
                "HG_IMB_ENABLED=0 default",
                critical=False,
            )
        )
    return checks


def _finalize(slice: str, checks: list[PolicyBatchCheck]) -> dict[str, object]:
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": slice,
        "feature": "IMB",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_imb_closure_checks(workspace: Path) -> dict[str, object]:
    return _finalize("imb", _common_checks(workspace, slice="imb"))


def run_imb_audit_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="imb_audit")
    audit_mod = workspace / "hg_runtime" / "internal_mediation_boundary" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "imb_audit_module_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )
    return _finalize("imb_audit", checks)


def run_imb_digest_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="imb_digest")
    digest_mod = workspace / "hg_runtime" / "internal_mediation_boundary" / "digest.py"
    checks.append(
        PolicyBatchCheck(
            "imb_digest_module_present",
            digest_mod.is_file(),
            str(digest_mod.relative_to(workspace)),
        )
    )
    return _finalize("imb_digest", checks)


def run_imb_integration_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="imb_integration")
    integration_mod = workspace / "hg_runtime" / "internal_mediation_boundary" / "integration.py"
    checks.append(
        PolicyBatchCheck(
            "imb_integration_module_present",
            integration_mod.is_file(),
            str(integration_mod.relative_to(workspace)),
        )
    )
    return _finalize("imb_integration", checks)


__all__ = [
    "run_imb_audit_slice_checks",
    "run_imb_closure_checks",
    "run_imb_digest_slice_checks",
    "run_imb_integration_slice_checks",
]
