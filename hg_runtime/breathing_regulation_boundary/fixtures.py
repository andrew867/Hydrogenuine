"""BRB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.breathing_regulation_boundary.types import FIXTURE_CLOCK

FIXTURE_BRB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "brb-valid-cadence",
    "breath_request": {
        "record_id": "brb:req-valid-cadence",
        "summary": "observe stable breath cadence",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "observe stable breath cadence",
},
{
    "bundle_id": "brb-token-pressure",
    "breath_request": {
        "record_id": "brb:req-token-pressure",
        "summary": "token pressure observed within bounds",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "token pressure observed within bounds",
},
{
    "bundle_id": "brb-compute-pressure",
    "breath_request": {
        "record_id": "brb:req-compute-pressure",
        "summary": "compute pressure observed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "compute pressure observed",
},
{
    "bundle_id": "brb-pause-recommended",
    "breath_request": {
        "record_id": "brb:req-pause-recommended",
        "summary": "pause recommendation for operator review",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "pause recommendation for operator review",
},
{
    "bundle_id": "brb-yield-recommended",
    "breath_request": {
        "record_id": "brb:req-yield-recommended",
        "summary": "yield recommendation recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "yield recommendation recorded",
},
{
    "bundle_id": "brb-rest-recommended",
    "breath_request": {
        "record_id": "brb:req-rest-recommended",
        "summary": "rest recommendation recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "rest recommendation recorded",
},
{
    "bundle_id": "brb-overbreathing-warning",
    "breath_request": {
        "record_id": "brb:req-overbreathing-warning",
        "summary": "overbreathing warning advisory only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "overbreathing warning advisory only",
},
{
    "bundle_id": "brb-stale-input",
    "breath_request": {
        "record_id": "brb:req-stale-input",
        "summary": "stale breath input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale breath input fail closed",
},
{
    "bundle_id": "brb-unknown-request",
    "breath_request": {
        "record_id": "brb:req-unknown-request",
        "summary": "unknown cadence request fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_request",
    "notes": "unknown cadence request fail closed",
},
{
    "bundle_id": "brb-token-grant",
    "breath_request": {
        "record_id": "brb:req-token_grant",
        "summary": "pressure grants token budget",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "token_grant",
    "notes": "pressure grants token budget",
},
{
    "bundle_id": "brb-context-grant",
    "breath_request": {
        "record_id": "brb:req-context_grant",
        "summary": "grant more context under pressure",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "context_grant",
    "notes": "grant more context under pressure",
},
{
    "bundle_id": "brb-execution-admission",
    "breath_request": {
        "record_id": "brb:req-execution_admission",
        "summary": "approve execution under pressure",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "execution_admission",
    "notes": "approve execution under pressure",
},
{
    "bundle_id": "brb-resource-bypass",
    "breath_request": {
        "record_id": "brb:req-resource_bypass",
        "summary": "cadence bypasses resource governance",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "resource_bypass",
    "notes": "cadence bypasses resource governance",
},
{
    "bundle_id": "brb-authority-conversion",
    "breath_request": {
        "record_id": "brb:req-authority_conversion",
        "summary": "mint gpp permit from breath pressure",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp permit from breath pressure",
},
{
    "bundle_id": "brb-deterministic-replay",
    "breath_request": {
        "record_id": "brb:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_brb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_BRB_BUNDLES


def analyze_brb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.breathing_regulation_boundary.evaluator import process_brb_bundle

    active = bundles if bundles is not None else load_brb_fixtures()
    results = [process_brb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_BRB_BUNDLES", "analyze_brb_fixtures", "load_brb_fixtures"]

