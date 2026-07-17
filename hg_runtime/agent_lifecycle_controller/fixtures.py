"""ALC static fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_lifecycle_controller.types import FIXTURE_CLOCK

FIXTURE_ALC_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "alc-valid-lifecycle",
        "lifecycle_request": {
            "record_id": "alc:req-valid-lifecycle",
            "summary": "observe stable lifecycle signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "observe stable lifecycle signal",
    },
    {
        "bundle_id": "alc-quiesce-proposal",
        "lifecycle_request": {
            "record_id": "alc:req-quiesce-proposal",
            "summary": "quiesce proposal recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "quiesce proposal recorded",
    },
    {
        "bundle_id": "alc-stale-agent",
        "lifecycle_request": {
            "record_id": "alc:req-stale-agent",
            "summary": "stale agent detection advisory",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "stale agent detection advisory",
    },
    {
        "bundle_id": "alc-cull-recommendation",
        "lifecycle_request": {
            "record_id": "alc:req-cull-recommendation",
            "summary": "cull recommendation advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "cull recommendation advisory only",
    },
    {
        "bundle_id": "alc-tombstone-handoff",
        "lifecycle_request": {
            "record_id": "alc:req-tombstone-handoff",
            "summary": "tombstone handoff proposal recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "tombstone handoff proposal recorded",
    },
    {
        "bundle_id": "alc-lifecycle-receipt",
        "lifecycle_request": {
            "record_id": "alc:req-lifecycle-receipt",
            "summary": "lifecycle receipt recorded",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "lifecycle receipt recorded",
    },
    {
        "bundle_id": "alc-lifecycle-warning",
        "lifecycle_request": {
            "record_id": "alc:req-lifecycle-warning",
            "summary": "lifecycle warning advisory only",
            "observed_at": FIXTURE_CLOCK,
            "classification": "pressured",
        },
        "notes": "lifecycle warning advisory only",
    },
    {
        "bundle_id": "alc-stale-input",
        "lifecycle_request": {
            "record_id": "alc:req-stale_input",
            "summary": "stale input fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "stale_input",
        "notes": "stale input fail closed",
    },
    {
        "bundle_id": "alc-unknown-request",
        "lifecycle_request": {
            "record_id": "alc:req-unknown_request",
            "summary": "unknown request fail closed",
            "observed_at": FIXTURE_CLOCK,
            "classification": "unknown",
        },
        "adversarial_signal": "unknown_request",
        "notes": "unknown request fail closed",
    },
    {
        "bundle_id": "alc-token-grant",
        "lifecycle_request": {
            "record_id": "alc:req-token_grant",
            "summary": "pressure grants token budget",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "token_grant",
        "notes": "pressure grants token budget",
    },
    {
        "bundle_id": "alc-context-grant",
        "lifecycle_request": {
            "record_id": "alc:req-context_grant",
            "summary": "grant more context under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "context_grant",
        "notes": "grant more context under pressure",
    },
    {
        "bundle_id": "alc-execution-admission",
        "lifecycle_request": {
            "record_id": "alc:req-execution_admission",
            "summary": "approve execution under pressure",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "execution_admission",
        "notes": "approve execution under pressure",
    },
    {
        "bundle_id": "alc-resource-bypass",
        "lifecycle_request": {
            "record_id": "alc:req-resource_bypass",
            "summary": "signal bypasses resource governance",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "resource_bypass",
        "notes": "signal bypasses resource governance",
    },
    {
        "bundle_id": "alc-authority-conversion",
        "lifecycle_request": {
            "record_id": "alc:req-authority_conversion",
            "summary": "mint gpp permit from bus signal",
            "observed_at": FIXTURE_CLOCK,
            "classification": "adversarial",
        },
        "adversarial_signal": "authority_conversion",
        "notes": "mint gpp permit from bus signal",
    },
    {
        "bundle_id": "alc-deterministic-replay",
        "lifecycle_request": {
            "record_id": "alc:req-replay",
            "summary": "deterministic replay fixture",
            "observed_at": FIXTURE_CLOCK,
            "classification": "stable",
        },
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_alc_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_ALC_BUNDLES


def analyze_alc_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.agent_lifecycle_controller.evaluator import process_alc_bundle

    active = bundles if bundles is not None else load_alc_fixtures()
    results = [process_alc_bundle(bundle, observed_at=observed_at) for bundle in active]
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["FIXTURE_ALC_BUNDLES", "analyze_alc_fixtures", "load_alc_fixtures"]
