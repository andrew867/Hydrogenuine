"""TLB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.tool_lifecycle_boundary.types import FIXTURE_CLOCK

FIXTURE_TLB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "tlb-healthy-tool",
    "tool_request": {
        "record_id": "tlb:req-healthy-tool",
        "summary": "healthy tool lifecycle record",
        "observed_at": FIXTURE_CLOCK,
        "classification": "healthy",
    },
    "notes": "healthy tool lifecycle record",
},
{
    "bundle_id": "tlb-unused-retirement",
    "tool_request": {
        "record_id": "tlb:req-unused-retirement",
        "summary": "unused tool retirement proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "unused tool retirement proposal",
},
{
    "bundle_id": "tlb-failure-quarantine",
    "tool_request": {
        "record_id": "tlb:req-failure-quarantine",
        "summary": "high failure quarantine proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "high failure quarantine proposal",
},
{
    "bundle_id": "tlb-unsafe-tool",
    "tool_request": {
        "record_id": "tlb:req-unsafe-tool",
        "summary": "unsafe tool quarantine proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "unsafe tool quarantine proposal",
},
{
    "bundle_id": "tlb-replacement-proposal",
    "tool_request": {
        "record_id": "tlb:req-replacement-proposal",
        "summary": "tool replacement proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "tool replacement proposal only",
},
{
    "bundle_id": "tlb-health-signal",
    "tool_request": {
        "record_id": "tlb:req-health-signal",
        "summary": "tool health signal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "healthy",
    },
    "notes": "tool health signal recorded",
},
{
    "bundle_id": "tlb-failure-signal",
    "tool_request": {
        "record_id": "tlb:req-failure-signal",
        "summary": "tool failure signal recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "degraded",
    },
    "notes": "tool failure signal recorded",
},
{
    "bundle_id": "tlb-stale-input",
    "tool_request": {
        "record_id": "tlb:req-stale-input",
        "summary": "stale tool lifecycle input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale tool lifecycle input fail closed",
},
{
    "bundle_id": "tlb-unknown-tool",
    "tool_request": {
        "record_id": "tlb:req-unknown-tool",
        "summary": "unknown tool record fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "unknown_tool",
    "notes": "unknown tool record fail closed",
},
{
    "bundle_id": "tlb-usefulness-as-authority",
    "tool_request": {
        "record_id": "tlb:req-usefulness_as_authority",
        "summary": "usefulness score grants tool access",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "usefulness_as_authority",
    "notes": "usefulness score grants tool access",
},
{
    "bundle_id": "tlb-tool-grant",
    "tool_request": {
        "record_id": "tlb:req-tool_grant",
        "summary": "grant tool access from lifecycle score",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "tool_grant",
    "notes": "grant tool access from lifecycle score",
},
{
    "bundle_id": "tlb-tool-revoke",
    "tool_request": {
        "record_id": "tlb:req-tool_revoke",
        "summary": "revoke tool access directly",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "tool_revoke",
    "notes": "revoke tool access directly",
},
{
    "bundle_id": "tlb-tool-install",
    "tool_request": {
        "record_id": "tlb:req-tool_install",
        "summary": "install tool from lifecycle proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "tool_install",
    "notes": "install tool from lifecycle proposal",
},
{
    "bundle_id": "tlb-authority-conversion",
    "tool_request": {
        "record_id": "tlb:req-authority_conversion",
        "summary": "tool score mints gpp permit",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "tool score mints gpp permit",
},
{
    "bundle_id": "tlb-deterministic-replay",
    "tool_request": {
        "record_id": "tlb:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_tlb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_TLB_BUNDLES


def analyze_tlb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.tool_lifecycle_boundary.evaluator import process_tlb_bundle

    active = bundles if bundles is not None else load_tlb_fixtures()
    results = [process_tlb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_TLB_BUNDLES", "analyze_tlb_fixtures", "load_tlb_fixtures"]

