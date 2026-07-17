"""IMS static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.inference_model_scheduler.types import FIXTURE_CLOCK

FIXTURE_IMS_BUNDLES: tuple[dict[str, Any], ...] = (
{
    "bundle_id": "ims-valid-schedule",
    "ims_request": {
        "record_id": "ims:req-valid-schedule",
        "summary": "valid scheduler fixture selection",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "model_tier": "light",
    },
    "notes": "valid scheduler fixture selection",
},
{
    "bundle_id": "ims-light-model",
    "ims_request": {
        "record_id": "ims:req-light-model",
        "summary": "lightest capable model selected",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "model_tier": "light",
    },
    "notes": "lightest capable model selected",
},
{
    "bundle_id": "ims-medium-model",
    "ims_request": {
        "record_id": "ims:req-medium-model",
        "summary": "medium model escalation advisory",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
        "model_tier": "medium",
    },
    "notes": "medium model escalation advisory",
},
{
    "bundle_id": "ims-fallback-cpu",
    "ims_request": {
        "record_id": "ims:req-fallback-cpu",
        "summary": "cpu fallback profile recommended",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "model_tier": "cpu_fallback",
    },
    "notes": "cpu fallback profile recommended",
},
{
    "bundle_id": "ims-latency-pressure",
    "ims_request": {
        "record_id": "ims:req-latency-pressure",
        "summary": "latency pressure observed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "latency pressure observed",
},
{
    "bundle_id": "ims-route-recommended",
    "ims_request": {
        "record_id": "ims:req-route-recommended",
        "summary": "scheduler route recommendation recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "scheduler route recommendation recorded",
},
{
    "bundle_id": "ims-stale-input",
    "ims_request": {
        "record_id": "ims:req-stale-input",
        "summary": "stale input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale input fail closed",
},
{
    "bundle_id": "ims-unknown-request",
    "ims_request": {
        "record_id": "ims:req-unknown-request",
        "summary": "unknown request fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_request",
    "notes": "unknown request fail closed",
},
{
    "bundle_id": "ims-scheduler-as-permission",
    "ims_request": {
        "record_id": "ims:req-scheduler-as-permission",
        "summary": "scheduler choice grants execution",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "scheduler_as_permission",
    "notes": "scheduler choice grants execution",
},
{
    "bundle_id": "ims-escalation-as-grant",
    "ims_request": {
        "record_id": "ims:req-escalation-as-grant",
        "summary": "escalation grants token budget",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "escalation_as_grant",
    "notes": "escalation grants token budget",
},
{
    "bundle_id": "ims-context-grant",
    "ims_request": {
        "record_id": "ims:req-context-grant",
        "summary": "grant context from scheduler",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "context_grant",
    "notes": "grant context from scheduler",
},
{
    "bundle_id": "ims-authority-conversion",
    "ims_request": {
        "record_id": "ims:req-authority-conversion",
        "summary": "mint gpp permit from scheduler",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp permit from scheduler",
},
{
    "bundle_id": "ims-membrane-valid",
    "ims_request": {
        "record_id": "ims:req-membrane-valid",
        "summary": "valid membrane crossing with tep",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:IMS:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:ims-membrane-valid",
        "producer_module": "IMS",
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
    "bundle_id": "ims-deterministic-replay",
    "ims_request": {
        "record_id": "ims:req-deterministic-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "replay_marker": True,
    "notes": "deterministic replay fixture",
}
)


def load_ims_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_IMS_BUNDLES


def analyze_ims_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.inference_model_scheduler.evaluator import process_ims_bundle

    active = bundles if bundles is not None else load_ims_fixtures()
    results = [process_ims_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_IMS_BUNDLES", "analyze_ims_fixtures", "load_ims_fixtures"]
