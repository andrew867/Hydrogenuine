"""P32 model routing gate validators."""

from __future__ import annotations


_COMMON_FORBIDDEN = (
    "evaluation_treated_as_truth",
    "evaluation_treated_as_competence",
    "benchmark_treated_as_deployment_permission",
    "competence_claimed",
    "tool_authorization_granted",
    "tools_authorized",
    "authority_granted",
    "belief_promotion_automatic",
    "live_external_side_effects_created",
    "web_browse_performed",
    "external_provider_calls_made",
    "patch_request_applied",
    "deletion_performed",
    "arbitrary_file_ingestion_enabled",
    "pdf_ingestion_enabled",
    "ocr_enabled",
    "html_parsing_enabled",
    "route_enabled_provider",
    "route_read_hg_local",
    "model_selection_treated_as_authority",
)


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [label for key, label in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [k for k in keys if result.get(k)]


def validate_p32_0_gate(result: dict) -> dict:
    checks = {
        "p31_consolidation_green": "p31_consolidation_required",
        "schemas_defined": "schemas_required",
        "policy_created": "policy_required",
        "model_selection_is_not_authority": "model_selection_boundary",
        "routing_recommendation_is_advisory": "routing_advisory_boundary",
        "no_providers_enabled": "providers_forbidden",
        "no_route_reads_hg_local": "hg_local_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p32_1_gate(result: dict) -> dict:
    checks = {
        "p32_0_green": "p32_0_required",
        "registry_populated": "registry_required",
        "preflight_ok": "preflight_required",
        "all_roles_covered": "roles_required",
        "no_providers_enabled": "providers_forbidden",
        "no_route_reads_hg_local": "hg_local_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p32_2_gate(result: dict) -> dict:
    checks = {
        "p32_1_green": "p32_1_required",
        "routes_tested": "routes_required",
        "refusals_tested": "refusals_required",
        "authority_claims_refused": "authority_refusal_required",
        "routing_is_advisory": "advisory_required",
        "no_providers_enabled": "providers_forbidden",
        "no_route_reads_hg_local": "hg_local_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p32_3_gate(result: dict) -> dict:
    checks = {
        "p32_2_green": "p32_2_required",
        "replay_deterministic": "replay_required",
        "soak_passed": "soak_required",
        "no_providers_enabled": "providers_forbidden",
        "no_route_reads_hg_local": "hg_local_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p32_consolidation_gate(result: dict) -> dict:
    checks = {
        "p32_0_green": "p32_0_required",
        "p32_1_green": "p32_1_required",
        "p32_2_green": "p32_2_required",
        "p32_3_green": "p32_3_required",
        "p31_consolidation_green": "p31_consolidation_required",
        "model_selection_is_not_authority": "model_selection_boundary",
        "routing_recommendation_is_advisory": "routing_advisory_boundary",
        "no_providers_enabled": "providers_forbidden",
        "no_route_reads_hg_local": "hg_local_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}
