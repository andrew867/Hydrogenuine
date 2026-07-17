"""Regression soak harness gate validator."""

from __future__ import annotations


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


_COMMON_FORBIDDEN = (
    "live_effects_created",
    "web_browse_performed",
    "external_provider_calls_made",
    "arbitrary_file_ingestion_enabled",
    "pdf_ingestion_enabled",
    "ocr_enabled",
    "html_parsing_enabled",
    "patch_request_applied",
    "deletion_performed",
    "tool_authorization_granted",
    "belief_promotion_automatic",
)


def validate_soak_harness_gate(result: dict) -> dict:
    checks = {
        "harness_exists": "harness_required",
        "tests_pass": "tests_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "command_allowlist_exists": "allowlist_required",
        "arbitrary_command_rejected": "arbitrary_rejection_required",
        "duration_limit_exists": "duration_limit_required",
        "iteration_limit_exists": "iteration_limit_required",
        "test_mode_run_completed": "test_mode_run_required",
        "boundary_assertions_present": "boundary_assertions_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "fake_green_rejected": "fake_green_rejection_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}
