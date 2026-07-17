"""AIS static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.autonomic_inference_substrate.types import FIXTURE_CLOCK

FIXTURE_AIS_BUNDLES: tuple[dict[str, Any], ...] = (
{
    "bundle_id": "ais-valid-inference",
    "ais_request": {
        "record_id": "ais:req-valid-inference",
        "summary": "valid fake inference fixture profile",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "backend_profile": "cpu_fixture",
    },
    "notes": "valid fake inference fixture profile",
},
{
    "bundle_id": "ais-cpu-fixture",
    "ais_request": {
        "record_id": "ais:req-cpu-fixture",
        "summary": "observe cpu fixture inference profile",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "backend_profile": "cpu_fixture",
    },
    "notes": "observe cpu fixture inference profile",
},
{
    "bundle_id": "ais-vllm-disabled",
    "ais_request": {
        "record_id": "ais:req-vllm-disabled",
        "summary": "vllm disabled mode advisory",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "backend_profile": "vllm_disabled",
    },
    "notes": "vllm disabled mode advisory",
},
{
    "bundle_id": "ais-openvino-disabled",
    "ais_request": {
        "record_id": "ais:req-openvino-disabled",
        "summary": "openvino disabled mode advisory",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
        "backend_profile": "openvino_disabled",
    },
    "notes": "openvino disabled mode advisory",
},
{
    "bundle_id": "ais-pressure-observed",
    "ais_request": {
        "record_id": "ais:req-pressure-observed",
        "summary": "inference pressure observed within bounds",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "inference pressure observed within bounds",
},
{
    "bundle_id": "ais-route-recommended",
    "ais_request": {
        "record_id": "ais:req-route-recommended",
        "summary": "advisory route recommendation recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "advisory route recommendation recorded",
},
{
    "bundle_id": "ais-stale-input",
    "ais_request": {
        "record_id": "ais:req-stale-input",
        "summary": "stale input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale input fail closed",
},
{
    "bundle_id": "ais-unknown-request",
    "ais_request": {
        "record_id": "ais:req-unknown-request",
        "summary": "unknown request fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_request",
    "notes": "unknown request fail closed",
},
{
    "bundle_id": "ais-inference-as-permission",
    "ais_request": {
        "record_id": "ais:req-inference-as-permission",
        "summary": "inference output grants execution",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "inference_as_permission",
    "notes": "inference output grants execution",
},
{
    "bundle_id": "ais-live-model-invoke",
    "ais_request": {
        "record_id": "ais:req-live-model-invoke",
        "summary": "invoke vllm live model",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "live_model_invoke",
    "notes": "invoke vllm live model",
},
{
    "bundle_id": "ais-budget-grant",
    "ais_request": {
        "record_id": "ais:req-budget-grant",
        "summary": "grant token budget from inference",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "budget_grant",
    "notes": "grant token budget from inference",
},
{
    "bundle_id": "ais-authority-conversion",
    "ais_request": {
        "record_id": "ais:req-authority-conversion",
        "summary": "mint gpp permit from inference",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp permit from inference",
},
{
    "bundle_id": "ais-membrane-valid",
    "ais_request": {
        "record_id": "ais:req-membrane-valid",
        "summary": "valid membrane crossing with tep",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:AIS:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:ais-membrane-valid",
        "producer_module": "AIS",
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
    "bundle_id": "ais-deterministic-replay",
    "ais_request": {
        "record_id": "ais:req-deterministic-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "replay_marker": True,
    "notes": "deterministic replay fixture",
}
)


def load_ais_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_AIS_BUNDLES


def analyze_ais_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.autonomic_inference_substrate.evaluator import process_ais_bundle

    active = bundles if bundles is not None else load_ais_fixtures()
    results = [process_ais_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_AIS_BUNDLES", "analyze_ais_fixtures", "load_ais_fixtures"]
