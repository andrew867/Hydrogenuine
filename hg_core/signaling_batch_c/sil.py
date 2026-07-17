"""SIL closure checks for Batch S5-C."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    sil_enabled,
    sil_refuse_silence_as_consent,
    sil_refuse_stale_recommendation,
    sil_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.silence_discipline.events import planned_sil_event_refs


def run_sil_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "silence_discipline"
    checks.append(PolicyBatchCheck("sil_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "silence_discipline_gate.py"
    checks.append(PolicyBatchCheck("sil_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "sil"
    checks.append(PolicyBatchCheck("sil_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "silence_discipline" / "SIL_SPEC.md"
    checks.append(PolicyBatchCheck("sil_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_sil_event_refs()
    checks.append(
        PolicyBatchCheck(
            "sil_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "sil_static_fixtures_only_default",
            sil_static_fixtures_only(),
            "HG_SIL_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sil_refuse_stale_recommendation_default",
            sil_refuse_stale_recommendation(),
            "HG_SIL_REFUSE_STALE_RECOMMENDATION=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "sil_refuse_silence_as_consent_default",
            sil_refuse_silence_as_consent(),
            "HG_SIL_REFUSE_SILENCE_AS_CONSENT=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "sil_disabled_by_default",
            not sil_enabled(),
            "HG_SIL_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "sil",
        "feature": "SIL",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_sil_closure_checks"]
