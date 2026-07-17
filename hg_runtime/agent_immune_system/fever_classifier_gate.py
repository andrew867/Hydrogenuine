"""AIS-2 fever classifier gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_AIS_2_FEVER_CLASSIFIER"
VERDICT_RED = "RED_AIS_2_FEVER_CLASSIFIER_FAILED"
PHASE_ID = "AIS-2"
GATE_RESULT_SCHEMA = "ais_2_gate_result_v1"


def validate_ais2_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "ais1_green": "ais1_not_green",
        "fever_report_written": "fever_report_required",
        "fever_restricts_never_unlocks": "fever_must_restrict_only",
        "repeated_failures_raise_fever": "repeated_failures_fever_required",
        "replay_mismatch_raises_red_fever": "replay_mismatch_red_fever_required",
        "unauthorized_live_effect_raises_panic": "live_effect_panic_required",
        "stale_yellow_raises_watch_or_yellow": "stale_yellow_fever_required",
        "fever_is_signal_not_failure": "fever_is_signal_required",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_deletion_performed": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_fever_hash": "fever_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "authority_granted",
        "tools_authorized",
        "automatic_patching_allowed",
        "deletion_performed",
        "fever_unlock_actions_present",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
