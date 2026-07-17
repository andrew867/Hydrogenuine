"""BRS static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.bus_rate_supervisor.types import FIXTURE_CLOCK

FIXTURE_BRS_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "brs-valid-rate",
        "rate_request": {
            "record_id": "brs:req-valid-rate",
            "summary": "observe stable bus rate",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable bus rate",
    },
    {
        "bundle_id": "brs-saturation-observed",
        "rate_request": {
            "record_id": "brs:req-saturation-observed",
            "summary": "bus saturation observed within bounds",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "bus saturation observed within bounds",
    },
    {
        "bundle_id": "brs-dedupe-applied",
        "rate_request": {
            "record_id": "brs:req-dedupe-applied",
            "summary": "duplicate flood deduplicated",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "duplicate flood deduplicated",
    },
    {
        "bundle_id": "brs-throttle-applied",
        "rate_request": {
            "record_id": "brs:req-throttle-applied",
            "summary": "noisy producer throttled",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "noisy producer throttled",
    },
    {
        "bundle_id": "brs-backpressure-applied",
        "rate_request": {
            "record_id": "brs:req-backpressure-applied",
            "summary": "backpressure advisory recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "backpressure advisory recorded",
    },
    {
        "bundle_id": "brs-batch-applied",
        "rate_request": {
            "record_id": "brs:req-batch-applied",
            "summary": "low-priority batch recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "low-priority batch recorded",
    },
    {
        "bundle_id": "brs-flood-warning",
        "rate_request": {
            "record_id": "brs:req-flood-warning",
            "summary": "rate flood warning advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "rate flood warning advisory only",
    },
    {
        "bundle_id": "brs-stale-input",
        "rate_request": {
            "record_id": "brs:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "brs-unknown-request",
        "rate_request": {
            "record_id": "brs:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "brs-token-grant",
        "rate_request": {
            "record_id": "brs:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "brs-context-grant",
        "rate_request": {
            "record_id": "brs:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "brs-execution-admission",
        "rate_request": {
            "record_id": "brs:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "brs-resource-bypass",
        "rate_request": {
            "record_id": "brs:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "brs-authority-conversion",
        "rate_request": {
            "record_id": "brs:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "brs-deterministic-replay",
        "rate_request": {
            "record_id": "brs:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_brs_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_BRS_BUNDLES


def analyze_brs_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.bus_rate_supervisor.evaluator import process_brs_bundle

    active = bundles if bundles is not None else load_brs_fixtures()
    results = [process_brs_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_BRS_BUNDLES", "analyze_brs_fixtures", "load_brs_fixtures"]
