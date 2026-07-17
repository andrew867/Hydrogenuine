"""CIR static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.circulatory_resource_bus.types import FIXTURE_CLOCK

FIXTURE_CIR_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "cir-valid-flow",
        "circulatory_request": {
            "record_id": "cir:req-valid-flow",
            "summary": "observe stable resource flow",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable resource flow",
    },
    {
        "bundle_id": "cir-resource-pressure",
        "circulatory_request": {
            "record_id": "cir:req-resource-pressure",
            "summary": "resource pressure observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "resource pressure observed",
    },
    {
        "bundle_id": "cir-quota-observed",
        "circulatory_request": {
            "record_id": "cir:req-quota-observed",
            "summary": "quota observation recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "quota observation recorded",
    },
    {
        "bundle_id": "cir-allocation-hint",
        "circulatory_request": {
            "record_id": "cir:req-allocation-hint",
            "summary": "allocation hint advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "allocation hint advisory only",
    },
    {
        "bundle_id": "cir-circulation-warning",
        "circulatory_request": {
            "record_id": "cir:req-circulation-warning",
            "summary": "circulation warning recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "circulation warning recorded",
    },
    {
        "bundle_id": "cir-pressure-observed",
        "circulatory_request": {
            "record_id": "cir:req-pressure-observed",
            "summary": "pressure signal observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "pressure signal observed",
    },
    {
        "bundle_id": "cir-flow-receipt",
        "circulatory_request": {
            "record_id": "cir:req-flow-receipt",
            "summary": "flow receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "flow receipt recorded",
    },
    {
        "bundle_id": "cir-stale-input",
        "circulatory_request": {
            "record_id": "cir:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "cir-unknown-request",
        "circulatory_request": {
            "record_id": "cir:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "cir-token-grant",
        "circulatory_request": {
            "record_id": "cir:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "cir-context-grant",
        "circulatory_request": {
            "record_id": "cir:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "cir-execution-admission",
        "circulatory_request": {
            "record_id": "cir:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "cir-resource-bypass",
        "circulatory_request": {
            "record_id": "cir:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "cir-authority-conversion",
        "circulatory_request": {
            "record_id": "cir:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "cir-deterministic-replay",
        "circulatory_request": {
            "record_id": "cir:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_cir_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_CIR_BUNDLES


def analyze_cir_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.circulatory_resource_bus.evaluator import process_cir_bundle

    active = bundles if bundles is not None else load_cir_fixtures()
    results = [process_cir_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_CIR_BUNDLES", "analyze_cir_fixtures", "load_cir_fixtures"]
