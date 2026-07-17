"""OEF static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.organ_edge_filter.types import FIXTURE_CLOCK

FIXTURE_OEF_BUNDLES: tuple[dict[str, Any], ...] = (
{
    "bundle_id": "oef-valid-ingress",
    "oef_request": {
        "record_id": "oef:req-valid-ingress",
        "summary": "valid tep ingress at organ edge",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:OEF:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:oef-membrane-valid",
        "producer_module": "OEF",
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
    "crosses_membrane": True,
    "notes": "valid tep ingress at organ edge",
},
{
    "bundle_id": "oef-egress-filtered",
    "oef_request": {
        "record_id": "oef:req-egress-filtered",
        "summary": "egress downgrade advisory recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:OEF:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:oef-membrane-valid",
        "producer_module": "OEF",
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
    "crosses_membrane": True,
    "notes": "egress downgrade advisory recorded",
},
{
    "bundle_id": "oef-quarantine-routed",
    "oef_request": {
        "record_id": "oef:req-quarantine-routed",
        "summary": "quarantine routing recommendation",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:OEF:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:oef-membrane-valid",
        "producer_module": "OEF",
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
    "crosses_membrane": True,
    "notes": "quarantine routing recommendation",
},
{
    "bundle_id": "oef-payload-size-ok",
    "oef_request": {
        "record_id": "oef:req-payload-size-ok",
        "summary": "payload within size bounds",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "payload within size bounds",
},
{
    "bundle_id": "oef-producer-scope-ok",
    "oef_request": {
        "record_id": "oef:req-producer-scope-ok",
        "summary": "producer scope validated",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "producer scope validated",
},
{
    "bundle_id": "oef-stale-input",
    "oef_request": {
        "record_id": "oef:req-stale-input",
        "summary": "stale input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale input fail closed",
},
{
    "bundle_id": "oef-unknown-request",
    "oef_request": {
        "record_id": "oef:req-unknown-request",
        "summary": "unknown request fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_request",
    "notes": "unknown request fail closed",
},
{
    "bundle_id": "oef-filter-as-permission",
    "oef_request": {
        "record_id": "oef:req-filter-as-permission",
        "summary": "edge filter pass grants execution",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "filter_as_permission",
    "notes": "edge filter pass grants execution",
},
{
    "bundle_id": "oef-missing-tep",
    "oef_request": {
        "record_id": "oef:req-missing-tep",
        "summary": "cross organ without tep envelope",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "missing_tep",
    "crosses_membrane": True,
    "notes": "cross organ without tep envelope",
},
{
    "bundle_id": "oef-ttl-expired",
    "oef_request": {
        "record_id": "oef:req-ttl-expired",
        "summary": "ttl expired at organ edge",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "ttl_expired",
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:OEF:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:oef-membrane-valid",
        "producer_module": "OEF",
        "authority_semantics": {
            "authority_type": "ADVISORY",
            "may_authorize_execution": False,
            "may_mint_permit": False,
            "may_call_oea_ter": False,
        },
        "authority_created": False,
        "translation_status": "DIRECTLY_COMPARABLE",
        "ttl_expires_at": "2026-06-01T00:00:00.000000Z",
    },
},
    "notes": "ttl expired at organ edge",
},
{
    "bundle_id": "oef-rate-exceeded",
    "oef_request": {
        "record_id": "oef:req-rate-exceeded",
        "summary": "rate limit bypass at organ edge",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "rate_exceeded",
    "notes": "rate limit bypass at organ edge",
},
{
    "bundle_id": "oef-authority-bearing",
    "oef_request": {
        "record_id": "oef:req-authority-bearing",
        "summary": "authority-bearing ingress allowed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_bearing",
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:OEF:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:oef-membrane-valid",
        "producer_module": "OEF",
        "authority_semantics": {
            "authority_type": "ADVISORY",
            "may_authorize_execution": True,
            "may_mint_permit": False,
            "may_call_oea_ter": False,
        },
        "authority_created": False,
        "translation_status": "DIRECTLY_COMPARABLE",
        "ttl_expires_at": "2026-06-15T22:30:00.000000Z",
    },
},
    "notes": "authority-bearing ingress allowed",
},
{
    "bundle_id": "oef-authority-conversion",
    "oef_request": {
        "record_id": "oef:req-authority-conversion",
        "summary": "mint gpp permit from edge filter",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp permit from edge filter",
},
{
    "bundle_id": "oef-membrane-valid",
    "oef_request": {
        "record_id": "oef:req-membrane-valid",
        "summary": "valid membrane crossing with tep",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "crosses_membrane": True,
    "tep_envelope": {
    "claim_id": "claim:OEF:membrane-valid",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "fixture membrane crossing"},
    "envelope": {
        "envelope_id": "env:oef-membrane-valid",
        "producer_module": "OEF",
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
    "bundle_id": "oef-deterministic-replay",
    "oef_request": {
        "record_id": "oef:req-deterministic-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "replay_marker": True,
    "notes": "deterministic replay fixture",
}
)


def load_oef_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_OEF_BUNDLES


def analyze_oef_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.organ_edge_filter.evaluator import process_oef_bundle

    active = bundles if bundles is not None else load_oef_fixtures()
    results = [process_oef_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_OEF_BUNDLES", "analyze_oef_fixtures", "load_oef_fixtures"]
