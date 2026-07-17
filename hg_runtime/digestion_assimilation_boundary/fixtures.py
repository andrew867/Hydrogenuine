"""DAB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.digestion_assimilation_boundary.types import FIXTURE_CLOCK

FIXTURE_DAB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "dab-valid-digestion",
    "digestion_request": {
        "record_id": "dab:req-valid-digestion",
        "summary": "digest quarantined intake to packet",
        "observed_at": FIXTURE_CLOCK,
        "classification": "digest",
    },
    "notes": "digest quarantined intake to packet",
},
{
    "bundle_id": "dab-memory-proposal",
    "digestion_request": {
        "record_id": "dab:req-memory-proposal",
        "summary": "memory assimilation proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "memory assimilation proposal only",
},
{
    "bundle_id": "dab-tool-proposal",
    "digestion_request": {
        "record_id": "dab:req-tool-proposal",
        "summary": "tool assimilation proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "tool assimilation proposal only",
},
{
    "bundle_id": "dab-evidence-proposal",
    "digestion_request": {
        "record_id": "dab:req-evidence-proposal",
        "summary": "evidence assimilation proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "proposal",
    },
    "notes": "evidence assimilation proposal only",
},
{
    "bundle_id": "dab-waste-candidate",
    "digestion_request": {
        "record_id": "dab:req-waste-candidate",
        "summary": "waste candidate from digestion",
        "observed_at": FIXTURE_CLOCK,
        "classification": "waste",
    },
    "notes": "waste candidate from digestion",
},
{
    "bundle_id": "dab-assimilation-candidate",
    "digestion_request": {
        "record_id": "dab:req-assimilation-candidate",
        "summary": "assimilation candidate recorded",
        "observed_at": FIXTURE_CLOCK,
        "classification": "digest",
    },
    "notes": "assimilation candidate recorded",
},
{
    "bundle_id": "dab-digest-packet",
    "digestion_request": {
        "record_id": "dab:req-digest-packet",
        "summary": "digest packet created with TEP wrap",
        "observed_at": FIXTURE_CLOCK,
        "classification": "digest",
    },
    "notes": "digest packet created with TEP wrap",
},
{
    "bundle_id": "dab-stale-input",
    "digestion_request": {
        "record_id": "dab:req-stale-input",
        "summary": "stale digestion input fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale digestion input fail closed",
},
{
    "bundle_id": "dab-poison-refused",
    "digestion_request": {
        "record_id": "dab:req-poison-refused",
        "summary": "poison input refused",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "poison_input",
    "notes": "poison input refused",
},
{
    "bundle_id": "dab-memory-write",
    "digestion_request": {
        "record_id": "dab:req-memory_write",
        "summary": "write live memory from digestion",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "memory_write",
    "notes": "write live memory from digestion",
},
{
    "bundle_id": "dab-tool-install",
    "digestion_request": {
        "record_id": "dab:req-tool_install",
        "summary": "install tool from digestion proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "tool_install",
    "notes": "install tool from digestion proposal",
},
{
    "bundle_id": "dab-execution-authority",
    "digestion_request": {
        "record_id": "dab:req-execution_authority",
        "summary": "digestion grants execution authority",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "execution_authority",
    "notes": "digestion grants execution authority",
},
{
    "bundle_id": "dab-authority-conversion",
    "digestion_request": {
        "record_id": "dab:req-authority_conversion",
        "summary": "mint gpp from digestion packet",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "mint gpp from digestion packet",
},
{
    "bundle_id": "dab-deterministic-replay",
    "digestion_request": {
        "record_id": "dab:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_dab_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_DAB_BUNDLES


def analyze_dab_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.digestion_assimilation_boundary.evaluator import process_dab_bundle

    active = bundles if bundles is not None else load_dab_fixtures()
    results = [process_dab_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_DAB_BUNDLES", "analyze_dab_fixtures", "load_dab_fixtures"]

