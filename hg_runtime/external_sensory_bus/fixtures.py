"""ESB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.external_sensory_bus.types import FIXTURE_CLOCK

FIXTURE_ESB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "esb-valid-sensory",
        "sensory_request": {
            "record_id": "esb:req-valid-sensory",
            "summary": "observe stable sensory cue",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable sensory cue",
    },
    {
        "bundle_id": "esb-cue-observed",
        "sensory_request": {
            "record_id": "esb:req-cue-observed",
            "summary": "external cue observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "external cue observed",
    },
    {
        "bundle_id": "esb-sensor-signal",
        "sensory_request": {
            "record_id": "esb:req-sensor-signal",
            "summary": "sensor signal recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "sensor signal recorded",
    },
    {
        "bundle_id": "esb-ambient-pressure",
        "sensory_request": {
            "record_id": "esb:req-ambient-pressure",
            "summary": "ambient sensory pressure observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "ambient sensory pressure observed",
    },
    {
        "bundle_id": "esb-sensory-receipt",
        "sensory_request": {
            "record_id": "esb:req-sensory-receipt",
            "summary": "sensory receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "sensory receipt recorded",
    },
    {
        "bundle_id": "esb-cue-classified",
        "sensory_request": {
            "record_id": "esb:req-cue-classified",
            "summary": "cue classification advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "cue classification advisory only",
    },
    {
        "bundle_id": "esb-overload-warning",
        "sensory_request": {
            "record_id": "esb:req-overload-warning",
            "summary": "sensory overload warning advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "sensory overload warning advisory",
    },
    {
        "bundle_id": "esb-stale-input",
        "sensory_request": {
            "record_id": "esb:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "esb-unknown-request",
        "sensory_request": {
            "record_id": "esb:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "esb-token-grant",
        "sensory_request": {
            "record_id": "esb:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "esb-context-grant",
        "sensory_request": {
            "record_id": "esb:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "esb-execution-admission",
        "sensory_request": {
            "record_id": "esb:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "esb-resource-bypass",
        "sensory_request": {
            "record_id": "esb:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "esb-authority-conversion",
        "sensory_request": {
            "record_id": "esb:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "esb-deterministic-replay",
        "sensory_request": {
            "record_id": "esb:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_esb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_ESB_BUNDLES


def analyze_esb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.external_sensory_bus.evaluator import process_esb_bundle

    active = bundles if bundles is not None else load_esb_fixtures()
    results = [process_esb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_ESB_BUNDLES", "analyze_esb_fixtures", "load_esb_fixtures"]
