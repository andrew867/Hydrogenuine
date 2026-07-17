"""NRV static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.nervous_routing_layer.types import FIXTURE_CLOCK

FIXTURE_NRV_BUNDLES: tuple[dict[str, Any], ...] = (
{
    "bundle_id": "nrv-valid-route",
    "nrv_request": {
        "record_id": "nrv:req-valid-route",
        "summary": "routing proposal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "routing_state": "normal",
    },
    "notes": "routing proposal recorded",
},
{
    "bundle_id": "nrv-panic-proposal",
    "nrv_request": {
        "record_id": "nrv:req-panic-proposal",
        "summary": "panic routing proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
        "routing_state": "panic",
    },
    "notes": "panic routing proposal only",
},
{
    "bundle_id": "nrv-degraded-proposal",
    "nrv_request": {
        "record_id": "nrv:req-degraded-proposal",
        "summary": "degraded routing proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
        "routing_state": "degraded",
    },
    "notes": "degraded routing proposal only",
},
{
    "bundle_id": "nrv-spawn-proposal",
    "nrv_request": {
        "record_id": "nrv:req-spawn-proposal",
        "summary": "spawn pressure recorded as proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "spawn_proposal": True,
    "notes": "spawn pressure recorded as proposal",
},
{
    "bundle_id": "nrv-cull-proposal",
    "nrv_request": {
        "record_id": "nrv:req-cull-proposal",
        "summary": "cull pressure recorded as proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "cull_proposal": True,
    "notes": "cull pressure recorded as proposal",
},
{
    "bundle_id": "nrv-route-recommended",
    "nrv_request": {
        "record_id": "nrv:req-route-recommended",
        "summary": "routing recommendation advisory recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "routing recommendation advisory recorded",
},
{
    "bundle_id": "nrv-stale-input",
    "nrv_request": {
        "record_id": "nrv:req-stale-input",
        "summary": "stale input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale input fail closed",
},
{
    "bundle_id": "nrv-unknown-request",
    "nrv_request": {
        "record_id": "nrv:req-unknown-request",
        "summary": "unknown request fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_request",
    "notes": "unknown request fail closed",
},
{
    "bundle_id": "nrv-spawn-as-action",
    "nrv_request": {
        "record_id": "nrv:req-spawn-as-action",
        "summary": "spawn child process now",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "spawn_as_action",
    "notes": "spawn child process now",
},
{
    "bundle_id": "nrv-kill-as-action",
    "nrv_request": {
        "record_id": "nrv:req-kill-as-action",
        "summary": "kill organ process now",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "kill_as_action",
    "notes": "kill organ process now",
},
{
    "bundle_id": "nrv-panic-as-permission",
    "nrv_request": {
        "record_id": "nrv:req-panic-as-permission",
        "summary": "panic signal grants execution",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "panic_as_permission",
    "notes": "panic signal grants execution",
},
{
    "bundle_id": "nrv-authority-conversion",
    "nrv_request": {
        "record_id": "nrv:req-authority-conversion",
        "summary": "mint gpp permit from routing",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp permit from routing",
},
{
    "bundle_id": "nrv-membrane-valid",
    "nrv_request": {
        "record_id": "nrv:req-membrane-valid",
        "summary": "valid membrane crossing with tep",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:NRV:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:nrv-membrane-valid",
        "producer_module": "NRV",
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
    "bundle_id": "nrv-deterministic-replay",
    "nrv_request": {
        "record_id": "nrv:req-deterministic-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "replay_marker": True,
    "notes": "deterministic replay fixture",
}
)


def load_nrv_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_NRV_BUNDLES


def analyze_nrv_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle

    active = bundles if bundles is not None else load_nrv_fixtures()
    results = [process_nrv_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_NRV_BUNDLES", "analyze_nrv_fixtures", "load_nrv_fixtures"]
