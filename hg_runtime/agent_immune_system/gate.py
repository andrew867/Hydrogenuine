"""AIS-0 schema foundation gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.agent_immune_system.schemas import INVARIANTS, RECORD_TYPES, VERDICT_RED


def validate_ais0_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "schemas_defined": "schemas_required",
        "invariants_documented": "invariants_required",
        "fever_restricts_never_unlocks": "fever_must_restrict_only",
        "quarantine_is_not_deletion": "quarantine_must_not_delete",
        "decay_is_not_erasure": "decay_must_not_erase",
        "security_audit_defensive_only": "security_must_be_defensive",
        "repair_recommendation_not_patch_permission": "repair_not_patch_permission",
        "immune_memory_append_only": "immune_memory_append_only_required",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_authority_grants": "authority_grants_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
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
        "decay_treated_as_deletion",
        "repair_recommendation_is_patch_permission",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "exploit_instructions_included",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("record_type_count", 0) < len(RECORD_TYPES):
        failures.append("record_types_incomplete")
    if result.get("invariant_count", 0) < len(INVARIANTS):
        failures.append("invariants_incomplete")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
