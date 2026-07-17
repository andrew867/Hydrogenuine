"""ORI closure checks for Batch ORI-A — full slice scope."""

from __future__ import annotations

from pathlib import Path

from hg_core.ori_cluster.batch_checks import ori_rtc_design_checks
from hg_core.ori_cluster.config import (
    ori_enabled,
    ori_refuse_authority_conversion,
    ori_refuse_stale_review,
    ori_static_fixtures_only,
)
from hg_core.ori_cluster.no_authority import check_ori_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.operator_review_intake.events import planned_ori_event_refs


def _common_checks(workspace: Path, *, slice: str) -> list[PolicyBatchCheck]:
    module = workspace / "hg_runtime" / "operator_review_intake"
    checks = [
        PolicyBatchCheck("ori_module_present", module.is_dir(), str(module.relative_to(workspace))),
        PolicyBatchCheck(
            "ori_gate_present",
            (workspace / "scripts" / "evals" / "ori_operator_review_gate.py").is_file(),
            "scripts/evals/ori_operator_review_gate.py",
        ),
        PolicyBatchCheck(
            "ori_spec_present",
            (workspace / "docs" / "planning" / "operator_review_intake" / "ORI_SPEC.md").is_file(),
            "docs/planning/operator_review_intake/ORI_SPEC.md",
        ),
    ]
    if slice == "ori":
        checks.extend(
            ori_rtc_design_checks(
                prefix="ori",
                events=planned_ori_event_refs(),
                minimum_events=15,
            )
        )
        checks.extend(
            [
                PolicyBatchCheck(
                    "ori_static_fixtures_only_default",
                    ori_static_fixtures_only(),
                    "HG_ORI_STATIC_FIXTURES_ONLY=1",
                ),
                PolicyBatchCheck(
                    "ori_refuse_stale_review_default",
                    ori_refuse_stale_review(),
                    "HG_ORI_REFUSE_STALE_REVIEW=1",
                ),
                PolicyBatchCheck(
                    "ori_refuse_authority_conversion_default",
                    ori_refuse_authority_conversion(),
                    "HG_ORI_REFUSE_AUTHORITY_CONVERSION=1",
                ),
            ]
        )
        fences_ok, fence_detail = check_ori_import_fences()
        checks.append(
            PolicyBatchCheck(
                "ori_import_fences",
                fences_ok,
                str(fence_detail) if not fences_ok else "clean",
            )
        )
        intake_fixtures = module / "intake_fixtures.py"
        checks.append(
            PolicyBatchCheck(
                "ori_static_intake_fixtures_present",
                intake_fixtures.is_file(),
                str(intake_fixtures.relative_to(workspace)),
            )
        )
        checks.append(
            PolicyBatchCheck(
                "ori_disabled_by_default",
                not ori_enabled(),
                "HG_ORI_ENABLED=0 default",
                critical=False,
            )
        )
    return checks


def _finalize(slice: str, checks: list[PolicyBatchCheck]) -> dict[str, object]:
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": slice,
        "feature": "ORI",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_ori_closure_checks(workspace: Path) -> dict[str, object]:
    return _finalize("ori", _common_checks(workspace, slice="ori"))


def run_ori_audit_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ori_audit")
    audit_mod = workspace / "hg_runtime" / "operator_review_intake" / "audit.py"
    checks.append(
        PolicyBatchCheck(
            "ori_audit_module_present",
            audit_mod.is_file(),
            str(audit_mod.relative_to(workspace)),
        )
    )
    return _finalize("ori_audit", checks)


def run_ori_digest_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ori_digest")
    digest_mod = workspace / "hg_runtime" / "operator_review_intake" / "digest.py"
    checks.append(
        PolicyBatchCheck(
            "ori_digest_module_present",
            digest_mod.is_file(),
            str(digest_mod.relative_to(workspace)),
        )
    )
    return _finalize("ori_digest", checks)


def run_ori_integration_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="ori_integration")
    integration_mod = workspace / "hg_runtime" / "operator_review_intake" / "integration.py"
    checks.append(
        PolicyBatchCheck(
            "ori_integration_module_present",
            integration_mod.is_file(),
            str(integration_mod.relative_to(workspace)),
        )
    )
    return _finalize("ori_integration", checks)


__all__ = [
    "run_ori_audit_slice_checks",
    "run_ori_closure_checks",
    "run_ori_digest_slice_checks",
    "run_ori_integration_slice_checks",
]
