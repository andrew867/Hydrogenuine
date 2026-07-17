"""OES schema foundation and phase gate validation."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import VERDICT_RED_OES0


def validate_oes0_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oec_consolidation_green": "oec_consolidation_required",
        "schemas_declared": "schemas_required",
        "soak_written": "soak_required",
        "policy_written": "policy_required",
        "manifest_written": "manifest_required",
        "iteration_written": "iteration_required",
        "replay_written": "replay_required",
        "boundary_written": "boundary_required",
        "mutation_probe_written": "mutation_probe_required",
        "mutation_result_written": "mutation_result_required",
        "soak_not_truth": "soak_truth_boundary",
        "replay_not_truth": "replay_truth_boundary",
        "determinism_not_correctness": "determinism_correctness_boundary",
        "mutation_not_repair": "mutation_repair_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "soak_treated_as_truth",
        "replay_match_treated_as_truth",
        "determinism_treated_as_correctness",
        "mutation_detection_is_repair",
        "mutation_auto_repaired",
        "belief_promotion_automatic",
        "deletion_performed",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_OES0, "failures": failures}


def validate_oes1_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oec_consolidation_green": "oec_consolidation_required",
        "oes0_green": "oes0_required",
        "iteration_count_met": "iteration_count_required",
        "all_iterations_match": "iteration_match_required",
        "stable_hashes_written": "stable_hashes_required",
        "explicit_corpus_manifest_only": "explicit_manifest_required",
        "old_proof_not_mutated": "old_proof_mutation_forbidden",
        "replay_not_truth": "replay_truth_boundary",
        "stable_hash_not_correctness": "stable_hash_correctness_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in ("replay_match_treated_as_truth", "mutation_auto_repaired", "belief_promotion_automatic"):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_oes2_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oec_consolidation_green": "oec_consolidation_required",
        "oes1_green": "oes1_required",
        "all_probe_types_exercised": "probe_types_required",
        "probes_written": "probes_required",
        "results_written": "results_required",
        "mismatches_detected": "mismatch_detection_required",
        "mutation_not_repair": "mutation_repair_boundary",
        "mutation_not_deletion": "mutation_deletion_boundary",
        "mutation_not_patch": "mutation_patch_boundary",
        "original_preserved": "original_preservation_boundary",
        "no_live_effects": "live_effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in ("mutation_detection_is_repair", "mutation_auto_repaired", "deletion_performed", "patch_request_applied"):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_oes3_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oec_consolidation_green": "oec_consolidation_required",
        "oes2_green": "oes2_required",
        "health_findings_written": "health_findings_required",
        "fever_reports_written": "fever_reports_required",
        "quarantine_candidates_written": "quarantine_candidates_required",
        "security_findings_written": "security_findings_required",
        "patch_hygiene_tasks_written": "patch_hygiene_tasks_required",
        "fever_restricts_never_unlocks": "fever_unlock_boundary",
        "quarantine_not_deletion": "quarantine_deletion_boundary",
        "security_defensive_only": "security_defensive_boundary",
        "patch_hygiene_not_patch": "patch_hygiene_boundary",
        "mutation_not_repair": "mutation_repair_boundary",
        "no_live_effects": "live_effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in ("fever_unlocks_action", "mutation_auto_repaired", "deletion_performed", "patch_request_applied"):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_oes_consolidation_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oec_consolidation_green": "oec_consolidation_required",
        "oes0_green": "oes0_required",
        "oes1_green": "oes1_required",
        "oes2_green": "oes2_required",
        "oes3_green": "oes3_required",
        "no_soak_as_truth": "soak_truth_forbidden",
        "no_replay_match_as_truth": "replay_truth_forbidden",
        "no_mutation_auto_repair": "mutation_repair_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_web_provider_live_effect": "web_provider_forbidden",
        "no_automatic_belief_promotion": "belief_promotion_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    return {"ok": not failures, "failures": failures}
