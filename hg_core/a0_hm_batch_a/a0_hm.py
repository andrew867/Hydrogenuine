"""A0-HM Batch A0-HM slice closure checks."""

from __future__ import annotations

from pathlib import Path

from hg_core.a0_hm_cluster.batch_checks import a0_hm_rtc_design_checks
from hg_core.a0_hm_cluster.config import (
    a0_hm_enabled,
    a0_hm_refuse_authority_conversion,
    a0_hm_refuse_spiritual_as_proof,
    a0_hm_static_fixtures_only,
)
from hg_core.a0_hm_cluster.no_authority import check_a0_hm_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_runtime.agent_zero_heart_mind.events import planned_a0_hm_event_refs


def _common_checks(workspace: Path, *, slice: str) -> list[PolicyBatchCheck]:
    module = workspace / "hg_runtime" / "agent_zero_heart_mind"
    checks = [
        PolicyBatchCheck(
            f"{slice}_module_present",
            module.is_dir(),
            str(module.relative_to(workspace)),
        ),
        PolicyBatchCheck(
            "a0_hm_gate_present",
            (workspace / "scripts" / "evals" / "a0_hm_heart_mind_gate.py").is_file(),
            "scripts/evals/a0_hm_heart_mind_gate.py",
        ),
        PolicyBatchCheck(
            "a0_hm_spec_present",
            (
                workspace / "docs" / "planning" / "agent_zero_heart_mind" / "A0_HM_SPEC.md"
            ).is_file(),
            "docs/planning/agent_zero_heart_mind/A0_HM_SPEC.md",
        ),
    ]
    if slice == "a0_hm":
        checks.extend(
            a0_hm_rtc_design_checks(
                prefix="a0_hm",
                events=planned_a0_hm_event_refs(),
                minimum_events=14,
            )
        )
        checks.extend(
            [
                PolicyBatchCheck(
                    "a0_hm_static_fixtures_only_default",
                    a0_hm_static_fixtures_only(),
                    "HG_A0_HM_STATIC_FIXTURES_ONLY=1",
                ),
                PolicyBatchCheck(
                    "a0_hm_refuse_authority_conversion_default",
                    a0_hm_refuse_authority_conversion(),
                    "HG_A0_HM_REFUSE_AUTHORITY_CONVERSION=1",
                ),
                PolicyBatchCheck(
                    "a0_hm_refuse_spiritual_as_proof_default",
                    a0_hm_refuse_spiritual_as_proof(),
                    "HG_A0_HM_REFUSE_SPIRITUAL_AS_PROOF=1",
                ),
            ]
        )
        fences_ok, fence_detail = check_a0_hm_import_fences()
        checks.append(
            PolicyBatchCheck(
                "a0_hm_import_fences",
                fences_ok,
                str(fence_detail) if not fences_ok else "clean",
            )
        )
        checks.append(
            PolicyBatchCheck(
                "a0_hm_route_table_present",
                (workspace / "hg_core" / "a0_hm_cluster" / "route_table.py").is_file(),
                "hg_core/a0_hm_cluster/route_table.py",
            )
        )
        checks.append(
            PolicyBatchCheck(
                "a0_hm_types_present",
                (module / "types.py").is_file(),
                "hg_runtime/agent_zero_heart_mind/types.py",
            )
        )
        checks.append(
            PolicyBatchCheck(
                "a0_hm_classifier_present",
                (module / "classifier.py").is_file(),
                "hg_runtime/agent_zero_heart_mind/classifier.py",
            )
        )
        checks.append(
            PolicyBatchCheck(
                "a0_hm_fixtures_present",
                (module / "fixtures.py").is_file(),
                "hg_runtime/agent_zero_heart_mind/fixtures.py",
            )
        )
        checks.append(
            PolicyBatchCheck(
                "a0_hm_disabled_by_default",
                not a0_hm_enabled(),
                "HG_A0_HM_ENABLED=0 default",
                critical=False,
            )
        )
    return checks


def _finalize(slice: str, checks: list[PolicyBatchCheck]) -> dict[str, object]:
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": slice,
        "feature": "A0-HM",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_a0_hm_closure_checks(workspace: Path) -> dict[str, object]:
    return _finalize("a0_hm", _common_checks(workspace, slice="a0_hm"))


def run_a0_hm_reception_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="a0_hm_reception")
    checks.append(
        PolicyBatchCheck(
            "a0_hm_reception_slice_present",
            (workspace / "hg_runtime" / "agent_zero_heart_mind" / "reception.py").is_file(),
            "reception.py",
        )
    )
    return _finalize("a0_hm_reception", checks)


def run_a0_hm_route_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="a0_hm_route")
    checks.append(
        PolicyBatchCheck(
            "a0_hm_router_slice_present",
            (workspace / "hg_runtime" / "agent_zero_heart_mind" / "router.py").is_file(),
            "router.py",
        )
    )
    return _finalize("a0_hm_route", checks)


def run_a0_hm_receipt_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="a0_hm_receipt")
    checks.append(
        PolicyBatchCheck(
            "a0_hm_receipt_slice_present",
            (workspace / "hg_runtime" / "agent_zero_heart_mind" / "receipt.py").is_file(),
            "receipt.py",
        )
    )
    return _finalize("a0_hm_receipt", checks)


def run_a0_hm_snapshot_slice_checks(workspace: Path) -> dict[str, object]:
    checks = _common_checks(workspace, slice="a0_hm_snapshot")
    checks.append(
        PolicyBatchCheck(
            "a0_hm_snapshot_slice_present",
            (workspace / "hg_runtime" / "agent_zero_heart_mind" / "snapshot.py").is_file(),
            "snapshot.py",
        )
    )
    return _finalize("a0_hm_snapshot", checks)


__all__ = [
    "run_a0_hm_closure_checks",
    "run_a0_hm_receipt_slice_checks",
    "run_a0_hm_reception_slice_checks",
    "run_a0_hm_route_slice_checks",
    "run_a0_hm_snapshot_slice_checks",
]
