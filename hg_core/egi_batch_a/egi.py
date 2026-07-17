"""EGI closure checks for Batch EGI-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.egi_cluster.batch_checks import egi_rtc_design_checks
from hg_core.egi_cluster.config import (
    egi_enabled,
    egi_refuse_authority_conversion,
    egi_refuse_stale_approval,
    egi_static_fixtures_only,
)
from hg_core.egi_cluster.events import planned_egi_event_refs
from hg_core.egi_cluster.no_authority import check_egi_import_fences
from hg_core.policy_batch_a.types import PolicyBatchCheck


def run_egi_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_core" / "egi"
    checks.append(PolicyBatchCheck("egi_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "egi_emergent_gap_gate.py"
    checks.append(PolicyBatchCheck("egi_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "egi"
    checks.append(PolicyBatchCheck("egi_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "emergent_gap_identifier" / "EGI_SPEC.md"
    checks.append(PolicyBatchCheck("egi_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    checks.extend(
        egi_rtc_design_checks(
            prefix="egi",
            events=planned_egi_event_refs(),
            minimum_events=12,
        )
    )

    checks.append(
        PolicyBatchCheck(
            "egi_static_fixtures_only_default",
            egi_static_fixtures_only(),
            "HG_EGI_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "egi_refuse_stale_approval_default",
            egi_refuse_stale_approval(),
            "HG_EGI_REFUSE_STALE_APPROVAL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "egi_refuse_authority_conversion_default",
            egi_refuse_authority_conversion(),
            "HG_EGI_REFUSE_AUTHORITY_CONVERSION=1",
        )
    )

    fences_ok, fence_detail = check_egi_import_fences()
    checks.append(
        PolicyBatchCheck("egi_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    fake_queue = workspace / "hg_core" / "egi" / "fake_queue.py"
    checks.append(
        PolicyBatchCheck(
            "egi_fake_queue_present",
            fake_queue.is_file(),
            str(fake_queue.relative_to(workspace)),
        )
    )

    packet_surface = workspace / "hg_runtime" / "emergent_gap_identifier" / "packet_surface.py"
    checks.append(
        PolicyBatchCheck(
            "egi_packet_surface_slice_present",
            packet_surface.is_file(),
            str(packet_surface.relative_to(workspace)),
        )
    )

    detector = workspace / "hg_core" / "egi" / "detector.py"
    checks.append(
        PolicyBatchCheck(
            "egi_fixture_detector_present",
            detector.is_file(),
            str(detector.relative_to(workspace)),
        )
    )

    checks.append(
        PolicyBatchCheck(
            "egi_disabled_by_default",
            not egi_enabled(),
            "HG_EGI_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "egi",
        "feature": "EGI",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_egi_packet_slice_checks(workspace: Path) -> dict[str, object]:
    packet_surface = workspace / "hg_runtime" / "emergent_gap_identifier" / "packet_surface.py"
    checks = [
        PolicyBatchCheck(
            "egi_packet_surface_module_present",
            packet_surface.is_file(),
            str(packet_surface.relative_to(workspace)),
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "egi_packet",
        "feature": "EGI",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


def run_egi_queue_slice_checks(workspace: Path) -> dict[str, object]:
    fake_queue = workspace / "hg_core" / "egi" / "fake_queue.py"
    checks = [
        PolicyBatchCheck(
            "egi_external_code_builder_queue_present",
            fake_queue.is_file(),
            str(fake_queue.relative_to(workspace)),
        ),
    ]
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "egi_queue",
        "feature": "EGI",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = [
    "run_egi_closure_checks",
    "run_egi_packet_slice_checks",
    "run_egi_queue_slice_checks",
]
