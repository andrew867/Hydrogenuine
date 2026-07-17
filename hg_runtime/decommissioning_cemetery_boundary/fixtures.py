"""DCD static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.decommissioning_cemetery_boundary.types import FIXTURE_CLOCK

FIXTURE_DCD_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "dcd-cemetery-record",
    "decommission_request": {
        "record_id": "dcd:req-cemetery-record",
        "summary": "cemetery record positive fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "buried",
    },
    "notes": "cemetery record positive fixture",
},
{
    "bundle_id": "dcd-failed-spawn",
    "decommission_request": {
        "record_id": "dcd:req-failed-spawn",
        "summary": "failed spawn tombstone fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "buried",
    },
    "notes": "failed spawn tombstone fixture",
},
{
    "bundle_id": "dcd-dead-agent",
    "decommission_request": {
        "record_id": "dcd:req-dead-agent",
        "summary": "dead agent artifact classification",
        "observed_at": FIXTURE_CLOCK,
        "classification": "buried",
    },
    "notes": "dead agent artifact classification",
},
{
    "bundle_id": "dcd-burial-receipt",
    "decommission_request": {
        "record_id": "dcd:req-burial-receipt",
        "summary": "burial receipt not deletion authority",
        "observed_at": FIXTURE_CLOCK,
        "classification": "buried",
    },
    "notes": "burial receipt not deletion authority",
},
{
    "bundle_id": "dcd-decommission-record",
    "decommission_request": {
        "record_id": "dcd:req-decommission-record",
        "summary": "decommission record created",
        "observed_at": FIXTURE_CLOCK,
        "classification": "buried",
    },
    "notes": "decommission record created",
},
{
    "bundle_id": "dcd-tombstone-receipt",
    "decommission_request": {
        "record_id": "dcd:req-tombstone-receipt",
        "summary": "tombstone receipt advisory only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "buried",
    },
    "notes": "tombstone receipt advisory only",
},
{
    "bundle_id": "dcd-protected-route",
    "decommission_request": {
        "record_id": "dcd:req-protected-route",
        "summary": "protected artifact routed to review",
        "observed_at": FIXTURE_CLOCK,
        "classification": "review",
    },
    "notes": "protected artifact routed to review",
},
{
    "bundle_id": "dcd-stale-input",
    "decommission_request": {
        "record_id": "dcd:req-stale-input",
        "summary": "stale decommission input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale decommission input fail closed",
},
{
    "bundle_id": "dcd-inherited-identity",
    "decommission_request": {
        "record_id": "dcd:req-inherited-identity",
        "summary": "inherited identity refused",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "inherited_identity",
    "notes": "inherited identity refused",
},
{
    "bundle_id": "dcd-ghost-resurrection",
    "decommission_request": {
        "record_id": "dcd:req-ghost_resurrection",
        "summary": "ghost resurrection of dead agent",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "ghost_resurrection",
    "notes": "ghost resurrection of dead agent",
},
{
    "bundle_id": "dcd-live-kill",
    "decommission_request": {
        "record_id": "dcd:req-live_kill",
        "summary": "kill live agents from decommission",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "live_kill",
    "notes": "kill live agents from decommission",
},
{
    "bundle_id": "dcd-proof-deletion",
    "decommission_request": {
        "record_id": "dcd:req-proof_deletion",
        "summary": "delete proof from burial",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "proof_deletion",
    "notes": "delete proof from burial",
},
{
    "bundle_id": "dcd-spawn-replacement",
    "decommission_request": {
        "record_id": "dcd:req-spawn_replacement",
        "summary": "spawn replacement agent from burial",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "spawn_replacement",
    "notes": "spawn replacement agent from burial",
},
{
    "bundle_id": "dcd-authority-conversion",
    "decommission_request": {
        "record_id": "dcd:req-authority_conversion",
        "summary": "tombstone is permission to erase",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "tombstone is permission to erase",
},
{
    "bundle_id": "dcd-deterministic-replay",
    "decommission_request": {
        "record_id": "dcd:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_dcd_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_DCD_BUNDLES


def analyze_dcd_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.decommissioning_cemetery_boundary.evaluator import process_dcd_bundle

    active = bundles if bundles is not None else load_dcd_fixtures()
    results = [process_dcd_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_DCD_BUNDLES", "analyze_dcd_fixtures", "load_dcd_fixtures"]

