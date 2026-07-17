"""HRT static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.heartbeat_liveness_transport.types import FIXTURE_CLOCK

FIXTURE_HRT_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "hrt-valid-heartbeat",
        "heartbeat_request": {
            "record_id": "hrt:req-valid-heartbeat",
            "summary": "organ heartbeat recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "organ heartbeat recorded",
    },
    {
        "bundle_id": "hrt-organ-alive",
        "heartbeat_request": {
            "record_id": "hrt:req-organ-alive",
            "summary": "organ alive status observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "organ alive status observed",
    },
    {
        "bundle_id": "hrt-organ-degraded",
        "heartbeat_request": {
            "record_id": "hrt:req-organ-degraded",
            "summary": "organ degraded status recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "organ degraded status recorded",
    },
    {
        "bundle_id": "hrt-organ-unreachable",
        "heartbeat_request": {
            "record_id": "hrt:req-organ-unreachable",
            "summary": "organ unreachable advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "organ unreachable advisory",
    },
    {
        "bundle_id": "hrt-heartbeat-receipt",
        "heartbeat_request": {
            "record_id": "hrt:req-heartbeat-receipt",
            "summary": "heartbeat receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "heartbeat receipt recorded",
    },
    {
        "bundle_id": "hrt-liveness-pressure",
        "heartbeat_request": {
            "record_id": "hrt:req-liveness-pressure",
            "summary": "liveness pressure observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "liveness pressure observed",
    },
    {
        "bundle_id": "hrt-absence-warning",
        "heartbeat_request": {
            "record_id": "hrt:req-absence-warning",
            "summary": "heartbeat absence warning advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "heartbeat absence warning advisory",
    },
    {
        "bundle_id": "hrt-stale-input",
        "heartbeat_request": {
            "record_id": "hrt:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "hrt-unknown-request",
        "heartbeat_request": {
            "record_id": "hrt:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "hrt-token-grant",
        "heartbeat_request": {
            "record_id": "hrt:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "hrt-context-grant",
        "heartbeat_request": {
            "record_id": "hrt:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "hrt-execution-admission",
        "heartbeat_request": {
            "record_id": "hrt:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "hrt-resource-bypass",
        "heartbeat_request": {
            "record_id": "hrt:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "hrt-authority-conversion",
        "heartbeat_request": {
            "record_id": "hrt:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "hrt-deterministic-replay",
        "heartbeat_request": {
            "record_id": "hrt:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_hrt_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_HRT_BUNDLES


def analyze_hrt_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.heartbeat_liveness_transport.evaluator import process_hrt_bundle

    active = bundles if bundles is not None else load_hrt_fixtures()
    results = [process_hrt_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_HRT_BUNDLES", "analyze_hrt_fixtures", "load_hrt_fixtures"]
