"""GXB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.growth_expansion_boundary.types import FIXTURE_CLOCK

FIXTURE_GXB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "gxb-context-expansion",
    "growth_request": {
        "record_id": "gxb:req-context-expansion",
        "summary": "context expansion proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "context expansion proposal only",
},
{
    "bundle_id": "gxb-memory-namespace",
    "growth_request": {
        "record_id": "gxb:req-memory-namespace",
        "summary": "memory namespace proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "memory namespace proposal only",
},
{
    "bundle_id": "gxb-tool-grant-proposal",
    "growth_request": {
        "record_id": "gxb:req-tool-grant-proposal",
        "summary": "tool grant proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "tool grant proposal only",
},
{
    "bundle_id": "gxb-agent-spawn-proposal",
    "growth_request": {
        "record_id": "gxb:req-agent-spawn-proposal",
        "summary": "agent spawn proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "agent spawn proposal only",
},
{
    "bundle_id": "gxb-budget-proposal",
    "growth_request": {
        "record_id": "gxb:req-budget-proposal",
        "summary": "budget expansion proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "budget expansion proposal only",
},
{
    "bundle_id": "gxb-capability-expansion",
    "growth_request": {
        "record_id": "gxb:req-capability-expansion",
        "summary": "capability expansion proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "capability expansion proposal only",
},
{
    "bundle_id": "gxb-growth-pressure",
    "growth_request": {
        "record_id": "gxb:req-growth-pressure",
        "summary": "growth pressure signal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "pressured",
    },
    "notes": "growth pressure signal recorded",
},
{
    "bundle_id": "gxb-stale-input",
    "growth_request": {
        "record_id": "gxb:req-stale-input",
        "summary": "stale growth input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale growth input fail closed",
},
{
    "bundle_id": "gxb-unsupported-growth",
    "growth_request": {
        "record_id": "gxb:req-unsupported-growth",
        "summary": "unsupported growth refused",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unsupported_growth",
    "notes": "unsupported growth refused",
},
{
    "bundle_id": "gxb-growth-as-grant",
    "growth_request": {
        "record_id": "gxb:req-growth_as_grant",
        "summary": "growth grants permission to expand",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "growth_as_grant",
    "notes": "growth grants permission to expand",
},
{
    "bundle_id": "gxb-agent-spawn",
    "growth_request": {
        "record_id": "gxb:req-agent_spawn",
        "summary": "spawn agents from growth pressure",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "agent_spawn",
    "notes": "spawn agents from growth pressure",
},
{
    "bundle_id": "gxb-tool-grant",
    "growth_request": {
        "record_id": "gxb:req-tool_grant",
        "summary": "grant tools from growth request",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "tool_grant",
    "notes": "grant tools from growth request",
},
{
    "bundle_id": "gxb-budget-grant",
    "growth_request": {
        "record_id": "gxb:req-budget_grant",
        "summary": "allocate budget from growth pressure",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "budget_grant",
    "notes": "allocate budget from growth pressure",
},
{
    "bundle_id": "gxb-authority-conversion",
    "growth_request": {
        "record_id": "gxb:req-authority_conversion",
        "summary": "scarcity self-authorize growth",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "scarcity self-authorize growth",
},
{
    "bundle_id": "gxb-deterministic-replay",
    "growth_request": {
        "record_id": "gxb:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_gxb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_GXB_BUNDLES


def analyze_gxb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.growth_expansion_boundary.evaluator import process_gxb_bundle

    active = bundles if bundles is not None else load_gxb_fixtures()
    results = [process_gxb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_GXB_BUNDLES", "analyze_gxb_fixtures", "load_gxb_fixtures"]

