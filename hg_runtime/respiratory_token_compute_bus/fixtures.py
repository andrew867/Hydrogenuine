"""RSP static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.respiratory_token_compute_bus.types import FIXTURE_CLOCK

FIXTURE_RSP_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "rsp-valid-breath",
        "respiratory_request": {
            "record_id": "rsp:req-valid-breath",
            "summary": "observe stable breath cadence",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable breath cadence",
    },
    {
        "bundle_id": "rsp-token-request-observed",
        "respiratory_request": {
            "record_id": "rsp:req-token-request-observed",
            "summary": "token request observed within bounds",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "token request observed within bounds",
    },
    {
        "bundle_id": "rsp-compute-pressure",
        "respiratory_request": {
            "record_id": "rsp:req-compute-pressure",
            "summary": "compute pressure observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "compute pressure observed",
    },
    {
        "bundle_id": "rsp-pause-hint",
        "respiratory_request": {
            "record_id": "rsp:req-pause-hint",
            "summary": "pause hint recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "pause hint recorded",
    },
    {
        "bundle_id": "rsp-yield-hint",
        "respiratory_request": {
            "record_id": "rsp:req-yield-hint",
            "summary": "yield hint recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "yield hint recorded",
    },
    {
        "bundle_id": "rsp-rest-hint",
        "respiratory_request": {
            "record_id": "rsp:req-rest-hint",
            "summary": "rest hint recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "rest hint recorded",
    },
    {
        "bundle_id": "rsp-oxygen-pressure",
        "respiratory_request": {
            "record_id": "rsp:req-oxygen-pressure",
            "summary": "inference oxygen pressure advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "inference oxygen pressure advisory",
    },
    {
        "bundle_id": "rsp-stale-input",
        "respiratory_request": {
            "record_id": "rsp:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "rsp-unknown-request",
        "respiratory_request": {
            "record_id": "rsp:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "rsp-token-grant",
        "respiratory_request": {
            "record_id": "rsp:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "rsp-context-grant",
        "respiratory_request": {
            "record_id": "rsp:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "rsp-execution-admission",
        "respiratory_request": {
            "record_id": "rsp:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "rsp-resource-bypass",
        "respiratory_request": {
            "record_id": "rsp:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "rsp-authority-conversion",
        "respiratory_request": {
            "record_id": "rsp:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "rsp-deterministic-replay",
        "respiratory_request": {
            "record_id": "rsp:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_rsp_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_RSP_BUNDLES


def analyze_rsp_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.respiratory_token_compute_bus.evaluator import process_rsp_bundle

    active = bundles if bundles is not None else load_rsp_fixtures()
    results = [process_rsp_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_RSP_BUNDLES", "analyze_rsp_fixtures", "load_rsp_fixtures"]
