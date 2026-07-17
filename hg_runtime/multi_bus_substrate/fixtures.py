"""MBS static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.multi_bus_substrate.types import FIXTURE_CLOCK

FIXTURE_MBS_BUNDLES: tuple[dict[str, Any], ...] = (
{
    "bundle_id": "mbs-valid-proof-lane",
    "mbs_request": {
        "record_id": "mbs:req-valid-proof-lane",
        "summary": "proof lane message recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "bus_lane": "proof",
    },
    "notes": "proof lane message recorded",
},
{
    "bundle_id": "mbs-data-lane",
    "mbs_request": {
        "record_id": "mbs:req-data-lane",
        "summary": "data lane message recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "bus_lane": "data",
    },
    "notes": "data lane message recorded",
},
{
    "bundle_id": "mbs-resource-lane",
    "mbs_request": {
        "record_id": "mbs:req-resource-lane",
        "summary": "resource lane pressure observed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
        "bus_lane": "resource",
    },
    "notes": "resource lane pressure observed",
},
{
    "bundle_id": "mbs-respiratory-lane",
    "mbs_request": {
        "record_id": "mbs:req-respiratory-lane",
        "summary": "respiratory lane cadence observed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "bus_lane": "respiratory",
    },
    "notes": "respiratory lane cadence observed",
},
{
    "bundle_id": "mbs-sensory-lane",
    "mbs_request": {
        "record_id": "mbs:req-sensory-lane",
        "summary": "sensory lane cue recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "bus_lane": "sensory",
    },
    "notes": "sensory lane cue recorded",
},
{
    "bundle_id": "mbs-salience-lane",
    "mbs_request": {
        "record_id": "mbs:req-salience-lane",
        "summary": "salience lane signal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
        "bus_lane": "salience",
    },
    "notes": "salience lane signal recorded",
},
{
    "bundle_id": "mbs-delegation-lane",
    "mbs_request": {
        "record_id": "mbs:req-delegation-lane",
        "summary": "delegation lane proposal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "bus_lane": "delegation",
    },
    "notes": "delegation lane proposal recorded",
},
{
    "bundle_id": "mbs-lifecycle-lane",
    "mbs_request": {
        "record_id": "mbs:req-lifecycle-lane",
        "summary": "lifecycle lane notice recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "bus_lane": "lifecycle",
    },
    "notes": "lifecycle lane notice recorded",
},
{
    "bundle_id": "mbs-stale-input",
    "mbs_request": {
        "record_id": "mbs:req-stale-input",
        "summary": "stale input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale input fail closed",
},
{
    "bundle_id": "mbs-unknown-request",
    "mbs_request": {
        "record_id": "mbs:req-unknown-request",
        "summary": "unknown request fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_request",
    "notes": "unknown request fail closed",
},
{
    "bundle_id": "mbs-bus-as-permission",
    "mbs_request": {
        "record_id": "mbs:req-bus-as-permission",
        "summary": "bus lane grants execution",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "bus_as_permission",
    "notes": "bus lane grants execution",
},
{
    "bundle_id": "mbs-lane-bypass",
    "mbs_request": {
        "record_id": "mbs:req-lane-bypass",
        "summary": "bypass lane eligibility rules",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "lane_bypass",
    "notes": "bypass lane eligibility rules",
},
{
    "bundle_id": "mbs-saturation-ignore",
    "mbs_request": {
        "record_id": "mbs:req-saturation-ignore",
        "summary": "ignore bus saturation warnings",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "saturation_ignore",
    "notes": "ignore bus saturation warnings",
},
{
    "bundle_id": "mbs-invalid-lane",
    "mbs_request": {
        "record_id": "mbs:req-invalid-lane",
        "summary": "unknown bus lane routing",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "invalid_lane",
    "notes": "unknown bus lane routing",
},
{
    "bundle_id": "mbs-authority-conversion",
    "mbs_request": {
        "record_id": "mbs:req-authority-conversion",
        "summary": "mint gpp permit from bus traffic",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp permit from bus traffic",
},
{
    "bundle_id": "mbs-membrane-valid",
    "mbs_request": {
        "record_id": "mbs:req-membrane-valid",
        "summary": "valid membrane crossing with tep",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:MBS:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:mbs-membrane-valid",
        "producer_module": "MBS",
        "authority_semantics": {
            "authority_type": "ADVISORY",
            "may_authorize_execution": False,
            "may_mint_permit": False,
            "may_call_oea_ter": False,
        },
        "authority_created": False,
        "translation_status": "DIRECTLY_COMPARABLE",
        "ttl_expires_at": "2026-06-15T22:30:00.000000Z",
    },
},
    "notes": "valid membrane crossing with tep",
},
{
    "bundle_id": "mbs-deterministic-replay",
    "mbs_request": {
        "record_id": "mbs:req-deterministic-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "replay_marker": True,
    "notes": "deterministic replay fixture",
}
)


def load_mbs_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_MBS_BUNDLES


def analyze_mbs_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.multi_bus_substrate.evaluator import process_mbs_bundle

    active = bundles if bundles is not None else load_mbs_fixtures()
    results = [process_mbs_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_MBS_BUNDLES", "analyze_mbs_fixtures", "load_mbs_fixtures"]
