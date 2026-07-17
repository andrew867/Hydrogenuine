"""SBS closure checks for Batch S5-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    sbs_enabled,
    sbs_refuse_expired_signal,
    sbs_refuse_proximity_as_permission,
    sbs_refuse_resonance_as_consent,
    sbs_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.semantic_birdsong.events import planned_sbs_event_refs


def run_sbs_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "semantic_birdsong"
    checks.append(PolicyBatchCheck("sbs_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "sbs_semantic_birdsong_gate.py"
    checks.append(PolicyBatchCheck("sbs_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "sbs"
    checks.append(PolicyBatchCheck("sbs_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "semantic_birdsong" / "SBS_SPEC.md"
    checks.append(PolicyBatchCheck("sbs_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_sbs_event_refs()
    checks.append(
        PolicyBatchCheck(
            "sbs_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "sbs_static_fixtures_only_default",
            sbs_static_fixtures_only(),
            "HG_SBS_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sbs_refuse_expired_signal_default",
            sbs_refuse_expired_signal(),
            "HG_SBS_REFUSE_EXPIRED_SIGNAL=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sbs_refuse_resonance_as_consent_default",
            sbs_refuse_resonance_as_consent(),
            "HG_SBS_REFUSE_RESONANCE_AS_CONSENT=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sbs_refuse_proximity_as_permission_default",
            sbs_refuse_proximity_as_permission(),
            "HG_SBS_REFUSE_PROXIMITY_AS_PERMISSION=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "sbs_disabled_by_default",
            not sbs_enabled(),
            "HG_SBS_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "sbs",
        "feature": "SBS",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_sbs_closure_checks"]
