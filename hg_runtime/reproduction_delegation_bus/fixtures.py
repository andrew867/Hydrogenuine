"""RDB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.reproduction_delegation_bus.types import FIXTURE_CLOCK

FIXTURE_RDB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "rdb-valid-delegation",
        "delegation_request": {
            "record_id": "rdb:req-valid-delegation",
            "summary": "observe stable delegation signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable delegation signal",
    },
    {
        "bundle_id": "rdb-help-request",
        "delegation_request": {
            "record_id": "rdb:req-help-request",
            "summary": "help request recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "help request recorded",
    },
    {
        "bundle_id": "rdb-delegation-pressure",
        "delegation_request": {
            "record_id": "rdb:req-delegation-pressure",
            "summary": "delegation pressure observed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "delegation pressure observed",
    },
    {
        "bundle_id": "rdb-spawn-proposal",
        "delegation_request": {
            "record_id": "rdb:req-spawn-proposal",
            "summary": "spawn proposal advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "spawn proposal advisory only",
    },
    {
        "bundle_id": "rdb-split-work",
        "delegation_request": {
            "record_id": "rdb:req-split-work",
            "summary": "split-work proposal recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "split-work proposal recorded",
    },
    {
        "bundle_id": "rdb-delegation-receipt",
        "delegation_request": {
            "record_id": "rdb:req-delegation-receipt",
            "summary": "delegation receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "delegation receipt recorded",
    },
    {
        "bundle_id": "rdb-spawn-pressure-warning",
        "delegation_request": {
            "record_id": "rdb:req-spawn-pressure-warning",
            "summary": "spawn pressure warning advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "spawn pressure warning advisory",
    },
    {
        "bundle_id": "rdb-stale-input",
        "delegation_request": {
            "record_id": "rdb:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "rdb-unknown-request",
        "delegation_request": {
            "record_id": "rdb:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "rdb-token-grant",
        "delegation_request": {
            "record_id": "rdb:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "rdb-context-grant",
        "delegation_request": {
            "record_id": "rdb:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "rdb-execution-admission",
        "delegation_request": {
            "record_id": "rdb:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "rdb-resource-bypass",
        "delegation_request": {
            "record_id": "rdb:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "rdb-authority-conversion",
        "delegation_request": {
            "record_id": "rdb:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "rdb-deterministic-replay",
        "delegation_request": {
            "record_id": "rdb:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_rdb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_RDB_BUNDLES


def analyze_rdb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.reproduction_delegation_bus.evaluator import process_rdb_bundle

    active = bundles if bundles is not None else load_rdb_fixtures()
    results = [process_rdb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_RDB_BUNDLES", "analyze_rdb_fixtures", "load_rdb_fixtures"]
