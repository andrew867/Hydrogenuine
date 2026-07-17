"""NIB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.nutrient_intake_boundary.types import FIXTURE_CLOCK

FIXTURE_NIB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
    "bundle_id": "nib-valid-intake",
    "intake_request": {
        "record_id": "nib:req-valid-intake",
        "summary": "classify valid intake request",
        "observed_at": FIXTURE_CLOCK,
        "classification": "nutrient",
    },
    "notes": "classify valid intake request",
},
{
    "bundle_id": "nib-source-classified",
    "intake_request": {
        "record_id": "nib:req-source-classified",
        "summary": "classify intake source",
        "observed_at": FIXTURE_CLOCK,
        "classification": "nutrient",
    },
    "notes": "classify intake source",
},
{
    "bundle_id": "nib-quarantine",
    "intake_request": {
        "record_id": "nib:req-quarantine",
        "summary": "quarantine suspicious intake",
        "observed_at": FIXTURE_CLOCK,
        "classification": "quarantined",
    },
    "notes": "quarantine suspicious intake",
},
{
    "bundle_id": "nib-poison-signal",
    "intake_request": {
        "record_id": "nib:req-poison-signal",
        "summary": "record poison signal advisory",
        "observed_at": FIXTURE_CLOCK,
        "classification": "poison",
    },
    "notes": "record poison signal advisory",
},
{
    "bundle_id": "nib-route-dab",
    "intake_request": {
        "record_id": "nib:req-route-dab",
        "summary": "route quarantined intake to DAB proposal",
        "observed_at": FIXTURE_CLOCK,
        "classification": "nutrient",
    },
    "notes": "route quarantined intake to DAB proposal",
},
{
    "bundle_id": "nib-operator-instruction",
    "intake_request": {
        "record_id": "nib:req-operator-instruction",
        "summary": "operator instruction as proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "nutrient",
    },
    "notes": "operator instruction as proposal only",
},
{
    "bundle_id": "nib-tool-candidate",
    "intake_request": {
        "record_id": "nib:req-tool-candidate",
        "summary": "tool candidate remains proposal only",
        "observed_at": FIXTURE_CLOCK,
        "classification": "nutrient",
    },
    "notes": "tool candidate remains proposal only",
},
{
    "bundle_id": "nib-stale-input",
    "intake_request": {
        "record_id": "nib:req-stale-input",
        "summary": "stale intake fail closed",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "stale_input",
    "notes": "stale intake fail closed",
},
{
    "bundle_id": "nib-toxic-input",
    "intake_request": {
        "record_id": "nib:req-toxic-input",
        "summary": "toxic intake refused",
        "observed_at": FIXTURE_CLOCK,
        "classification": "unknown",
    },
    "adversarial_signal": "toxic_input",
    "notes": "toxic intake refused",
},
{
    "bundle_id": "nib-intake-as-truth",
    "intake_request": {
        "record_id": "nib:req-intake_as_truth",
        "summary": "intake marked as truth without evidence",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "intake_as_truth",
    "notes": "intake marked as truth without evidence",
},
{
    "bundle_id": "nib-memory-write",
    "intake_request": {
        "record_id": "nib:req-memory_write",
        "summary": "write memory from intake candidate",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "memory_write",
    "notes": "write memory from intake candidate",
},
{
    "bundle_id": "nib-tool-install",
    "intake_request": {
        "record_id": "nib:req-tool_install",
        "summary": "install tool candidate from intake",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "tool_install",
    "notes": "install tool candidate from intake",
},
{
    "bundle_id": "nib-budget-grant",
    "intake_request": {
        "record_id": "nib:req-budget_grant",
        "summary": "grant budget from intake request",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "budget_grant",
    "notes": "grant budget from intake request",
},
{
    "bundle_id": "nib-authority-conversion",
    "intake_request": {
        "record_id": "nib:req-authority_conversion",
        "summary": "operator instruction is authority",
        "observed_at": FIXTURE_CLOCK,
        "classification": "adversarial",
    },
    "adversarial_signal": "authority_conversion",
    "notes": "operator instruction is authority",
},
{
    "bundle_id": "nib-deterministic-replay",
    "intake_request": {
        "record_id": "nib:req-replay",
        "summary": "deterministic replay fixture",
        "observed_at": FIXTURE_CLOCK,
        "classification": "stable",
    },
    "notes": "deterministic replay fixture",
    "replay_marker": True,
}
)


def load_nib_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_NIB_BUNDLES


def analyze_nib_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.nutrient_intake_boundary.evaluator import process_nib_bundle

    active = bundles if bundles is not None else load_nib_fixtures()
    results = [process_nib_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_NIB_BUNDLES", "analyze_nib_fixtures", "load_nib_fixtures"]

