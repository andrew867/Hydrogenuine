"""DAC closure checks for Batch S5-A."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.signaling.config import (
    dac_enabled,
    dac_refuse_bite_as_consent,
    dac_refuse_stale_cast,
    dac_static_fixtures_only,
)
from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_runtime.distributed_attention_casting.events import planned_dac_event_refs


def run_dac_closure_checks(workspace: Path) -> dict[str, object]:
    checks: list[PolicyBatchCheck] = []

    module = workspace / "hg_runtime" / "distributed_attention_casting"
    checks.append(PolicyBatchCheck("dac_module_present", module.is_dir(), str(module.relative_to(workspace))))

    gate = workspace / "scripts" / "evals" / "distributed_attention_casting_gate.py"
    checks.append(PolicyBatchCheck("dac_gate_present", gate.is_file(), str(gate.relative_to(workspace))))

    tests = workspace / "tests" / "dac"
    checks.append(PolicyBatchCheck("dac_tests_present", tests.is_dir(), str(tests.relative_to(workspace))))

    spec = workspace / "docs" / "planning" / "distributed_attention_casting" / "DAC_SPEC.md"
    checks.append(PolicyBatchCheck("dac_spec_present", spec.is_file(), str(spec.relative_to(workspace))))

    refs = planned_dac_event_refs()
    checks.append(
        PolicyBatchCheck(
            "dac_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in refs),
            f"refs={len(refs)}",
        )
    )

    checks.append(
        PolicyBatchCheck(
            "dac_static_fixtures_only_default",
            dac_static_fixtures_only(),
            "HG_DAC_STATIC_FIXTURES_ONLY=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "dac_refuse_stale_cast_default",
            dac_refuse_stale_cast(),
            "HG_DAC_REFUSE_STALE_CAST=1",
        )
    )
    checks.append(
        PolicyBatchCheck(
            "dac_refuse_bite_as_consent_default",
            dac_refuse_bite_as_consent(),
            "HG_DAC_REFUSE_BITE_AS_CONSENT=1",
        )
    )

    fences_ok, fence_detail = check_signaling_import_fences()
    checks.append(
        PolicyBatchCheck("signaling_import_fences", fences_ok, str(fence_detail) if not fences_ok else "clean")
    )

    checks.append(
        PolicyBatchCheck(
            "dac_disabled_by_default",
            not dac_enabled(),
            "HG_DAC_ENABLED=0 default",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "dac",
        "feature": "DAC",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["run_dac_closure_checks"]
