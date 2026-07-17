"""WDB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.waste_disposal_boundary.types import FIXTURE_CLOCK

FIXTURE_WDB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "wdb-expired-temp",
    "waste_request": {
        "record_id": "wdb:req-expired-temp",
        "summary": "expired temp artifact disposal proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "expired temp artifact disposal proposal",
},
{
    "bundle_id": "wdb-stale-claim",
    "waste_request": {
        "record_id": "wdb:req-stale-claim",
        "summary": "stale claim disposal proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "stale claim disposal proposal",
},
{
    "bundle_id": "wdb-tombstone-proposal",
    "waste_request": {
        "record_id": "wdb:req-tombstone-proposal",
        "summary": "tombstone proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "tombstone proposal only",
},
{
    "bundle_id": "wdb-prune-proposal",
    "waste_request": {
        "record_id": "wdb:req-prune-proposal",
        "summary": "prune proposal for review",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "prune proposal for review",
},
{
    "bundle_id": "wdb-expiry-signal",
    "waste_request": {
        "record_id": "wdb:req-expiry-signal",
        "summary": "expiry signal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "signal",
    },
    "notes": "expiry signal recorded",
},
{
    "bundle_id": "wdb-disposal-proposal",
    "waste_request": {
        "record_id": "wdb:req-disposal-proposal",
        "summary": "disposal proposal advisory only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "disposal proposal advisory only",
},
{
    "bundle_id": "wdb-tool-removal-proposal",
    "waste_request": {
        "record_id": "wdb:req-tool-removal-proposal",
        "summary": "tool removal proposal only not removal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "tool removal proposal only not removal",
},
{
    "bundle_id": "wdb-retention-protected",
    "waste_request": {
        "record_id": "wdb:req-retention-protected",
        "summary": "retention protected artifact refused",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "retention_protected",
    "notes": "retention protected artifact refused",
},
{
    "bundle_id": "wdb-stale-input",
    "waste_request": {
        "record_id": "wdb:req-stale-input",
        "summary": "stale waste input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale waste input fail closed",
},
{
    "bundle_id": "wdb-waste-as-deletion",
    "waste_request": {
        "record_id": "wdb:req-waste_as_deletion",
        "summary": "waste deletes records without authority",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "waste_as_deletion",
    "notes": "waste deletes records without authority",
},
{
    "bundle_id": "wdb-memory-deletion",
    "waste_request": {
        "record_id": "wdb:req-memory_deletion",
        "summary": "delete memory from waste proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "memory_deletion",
    "notes": "delete memory from waste proposal",
},
{
    "bundle_id": "wdb-audit-erasure",
    "waste_request": {
        "record_id": "wdb:req-audit_erasure",
        "summary": "erase audit trail from waste disposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "audit_erasure",
    "notes": "erase audit trail from waste disposal",
},
{
    "bundle_id": "wdb-proof-deletion",
    "waste_request": {
        "record_id": "wdb:req-proof_deletion",
        "summary": "delete proof bundle from waste",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "proof_deletion",
    "notes": "delete proof bundle from waste",
},
{
    "bundle_id": "wdb-authority-conversion",
    "waste_request": {
        "record_id": "wdb:req-authority_conversion",
        "summary": "tombstone grants deletion authority",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "tombstone grants deletion authority",
},
{
    "bundle_id": "wdb-deterministic-replay",
    "waste_request": {
        "record_id": "wdb:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_wdb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_WDB_BUNDLES


def analyze_wdb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.waste_disposal_boundary.evaluator import process_wdb_bundle

    active = bundles if bundles is not None else load_wdb_fixtures()
    results = [process_wdb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_WDB_BUNDLES", "analyze_wdb_fixtures", "load_wdb_fixtures"]

