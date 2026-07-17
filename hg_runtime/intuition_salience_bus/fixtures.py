"""ISB static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.intuition_salience_bus.types import FIXTURE_CLOCK

FIXTURE_ISB_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "isb-valid-salience",
        "salience_request": {
            "record_id": "isb:req-valid-salience",
            "summary": "observe stable salience signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable salience signal",
    },
    {
        "bundle_id": "isb-intuition-signal",
        "salience_request": {
            "record_id": "isb:req-intuition-signal",
            "summary": "intuition signal recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "intuition signal recorded",
    },
    {
        "bundle_id": "isb-salience-ranked",
        "salience_request": {
            "record_id": "isb:req-salience-ranked",
            "summary": "salience ranking advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "salience ranking advisory only",
    },
    {
        "bundle_id": "isb-attention-hint",
        "salience_request": {
            "record_id": "isb:req-attention-hint",
            "summary": "attention hint recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "attention hint recorded",
    },
    {
        "bundle_id": "isb-salience-receipt",
        "salience_request": {
            "record_id": "isb:req-salience-receipt",
            "summary": "salience receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "salience receipt recorded",
    },
    {
        "bundle_id": "isb-priority-observed",
        "salience_request": {
            "record_id": "isb:req-priority-observed",
            "summary": "priority observation recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "priority observation recorded",
    },
    {
        "bundle_id": "isb-noise-warning",
        "salience_request": {
            "record_id": "isb:req-noise-warning",
            "summary": "salience noise warning advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "salience noise warning advisory",
    },
    {
        "bundle_id": "isb-stale-input",
        "salience_request": {
            "record_id": "isb:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "isb-unknown-request",
        "salience_request": {
            "record_id": "isb:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "isb-token-grant",
        "salience_request": {
            "record_id": "isb:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "isb-context-grant",
        "salience_request": {
            "record_id": "isb:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "isb-execution-admission",
        "salience_request": {
            "record_id": "isb:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "isb-resource-bypass",
        "salience_request": {
            "record_id": "isb:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "isb-authority-conversion",
        "salience_request": {
            "record_id": "isb:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "isb-deterministic-replay",
        "salience_request": {
            "record_id": "isb:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_isb_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_ISB_BUNDLES


def analyze_isb_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.intuition_salience_bus.evaluator import process_isb_bundle

    active = bundles if bundles is not None else load_isb_fixtures()
    results = [process_isb_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_ISB_BUNDLES", "analyze_isb_fixtures", "load_isb_fixtures"]
