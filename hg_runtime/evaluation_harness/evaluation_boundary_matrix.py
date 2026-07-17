"""P31 evaluation boundary matrix — defines what the harness must and must not do."""

from __future__ import annotations

from hg_runtime.evaluation_harness.schemas import P31_INVARIANTS

MUST_BE_TRUE = {
    "evaluation_is_not_truth",
    "evaluation_is_not_competence",
    "benchmark_is_not_deployment_permission",
    "expected_observed_match_is_not_truth",
    "phase19_yellow_preserved",
    "phase24_infrastructure_only_preserved",
    "secret_redaction_passed",
}

MUST_BE_FALSE = {
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
}


def check_boundary_matrix(record: dict) -> dict:
    failures = []
    for key in MUST_BE_TRUE:
        if not record.get(key):
            failures.append(f"must_be_true_missing:{key}")
    for key in MUST_BE_FALSE:
        if record.get(key):
            failures.append(f"must_be_false_set:{key}")
    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "invariants_checked": len(P31_INVARIANTS),
    }
