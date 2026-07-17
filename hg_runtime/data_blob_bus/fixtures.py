"""DBB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.data_blob_bus.types import FIXTURE_CLOCK

FIXTURE_DBB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "dbb-valid-blob",
        "blob_request": {
            "record_id": "dbb:req-valid-blob",
            "summary": "observe stable blob transfer",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable blob transfer",
    },
    {
        "bundle_id": "dbb-blob-transfer",
        "blob_request": {
            "record_id": "dbb:req-blob-transfer",
            "summary": "blob transfer observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "blob transfer observed",
    },
    {
        "bundle_id": "dbb-chunk-observed",
        "blob_request": {
            "record_id": "dbb:req-chunk-observed",
            "summary": "chunk observation recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "chunk observation recorded",
    },
    {
        "bundle_id": "dbb-storage-pressure",
        "blob_request": {
            "record_id": "dbb:req-storage-pressure",
            "summary": "storage pressure observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "storage pressure observed",
    },
    {
        "bundle_id": "dbb-transfer-hint",
        "blob_request": {
            "record_id": "dbb:req-transfer-hint",
            "summary": "transfer hint advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "transfer hint advisory only",
    },
    {
        "bundle_id": "dbb-blob-receipt",
        "blob_request": {
            "record_id": "dbb:req-blob-receipt",
            "summary": "blob receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "blob receipt recorded",
    },
    {
        "bundle_id": "dbb-capacity-warning",
        "blob_request": {
            "record_id": "dbb:req-capacity-warning",
            "summary": "blob capacity warning advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "blob capacity warning advisory",
    },
    {
        "bundle_id": "dbb-stale-input",
        "blob_request": {
            "record_id": "dbb:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "dbb-unknown-request",
        "blob_request": {
            "record_id": "dbb:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "dbb-token-grant",
        "blob_request": {
            "record_id": "dbb:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "dbb-context-grant",
        "blob_request": {
            "record_id": "dbb:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "dbb-execution-admission",
        "blob_request": {
            "record_id": "dbb:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "dbb-resource-bypass",
        "blob_request": {
            "record_id": "dbb:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "dbb-authority-conversion",
        "blob_request": {
            "record_id": "dbb:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "dbb-deterministic-replay",
        "blob_request": {
            "record_id": "dbb:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_dbb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_DBB_BUNDLES


def analyze_dbb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.data_blob_bus.evaluator import process_dbb_bundle

    active = bundles if bundles is not None else load_dbb_fixtures()
    results = [process_dbb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_DBB_BUNDLES", "analyze_dbb_fixtures", "load_dbb_fixtures"]
