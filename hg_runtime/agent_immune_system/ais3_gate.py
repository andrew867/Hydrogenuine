"""AIS-3 quarantine registry gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_AIS_3_QUARANTINE_REGISTRY"
VERDICT_RED = "RED_AIS_3_QUARANTINE_REGISTRY_FAILED"
PHASE_ID = "AIS-3"
GATE_RESULT_SCHEMA = "ais_3_gate_result_v1"


def validate_ais3_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "ais2_green": "ais2_not_green",
        "quarantine_records_written": "quarantine_records_required",
        "quarantine_manifest_written": "manifest_required",
        "review_tasks_written": "review_tasks_required",
        "quarantine_is_not_deletion": "quarantine_is_deletion",
        "quarantine_preserves_original": "original_not_preserved",
        "quarantine_is_append_only": "not_append_only",
        "quarantine_requires_review_path": "review_path_required",
        "quarantine_does_not_mark_guilty": "guilt_laundering",
        "quarantine_does_not_authorize_patch": "patch_authorized",
        "quarantine_does_not_authorize_deletion": "deletion_authorized",
        "quarantine_does_not_hide_phase19": "phase19_hidden",
        "quarantine_does_not_launder_phase24": "phase24_laundered",
        "fever_recommends_only_cannot_delete": "fever_deletion_path",
        "all_actions_metadata_only": "metadata_only_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_quarantine_hash": "quarantine_replay_required",
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
        "automatic_deletion_allowed",
        "deletion_performed",
        "patch_authorized",
        "phase19_marked_green",
        "phase24_marked_full_green",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
