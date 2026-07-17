"""SQP schema foundation and phase gate validation."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import VERDICT_RED_SQP0


def validate_sqp0_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "schemas_declared": "schemas_required",
        "source_identity_written": "identity_required",
        "source_fingerprint_written": "fingerprint_required",
        "duplicate_record_written": "duplicate_required",
        "quality_score_written": "quality_required",
        "provenance_records_written": "provenance_required",
        "staleness_record_written": "staleness_required",
        "conflict_record_written": "conflict_required",
        "redaction_status_written": "redaction_required",
        "quarantine_history_written": "quarantine_required",
        "review_hint_written": "review_hint_required",
        "source_quality_not_truth": "quality_truth_boundary",
        "provenance_not_authority": "provenance_authority_boundary",
        "duplicate_not_corroboration": "duplicate_corroboration_boundary",
        "many_copies_not_many_sources": "copy_count_boundary",
        "stale_not_false": "stale_false_boundary",
        "low_quality_not_deletion": "quality_deletion_boundary",
        "review_hint_not_approval": "hint_approval_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_authority": "authority_forbidden",
        "no_tools": "tools_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
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
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "duplicate_treated_as_corroboration",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SQP0, "failures": failures}


def validate_sqp1_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp0_green": "sqp0_required",
        "source_manifests_consumed": "source_manifest_required",
        "evidence_receipts_consumed": "evidence_receipts_required",
        "reviewed_links_consumed": "reviewed_links_required",
        "source_identities_written": "source_identities_required",
        "source_fingerprints_written": "source_fingerprints_required",
        "duplicate_records_written": "duplicate_records_required",
        "all_duplicate_classes_exercised": "duplicate_classes_required",
        "exact_duplicate_detected": "exact_duplicate_required",
        "normalized_duplicate_detected": "normalized_duplicate_required",
        "same_source_different_excerpt_detected": "same_source_excerpt_required",
        "same_text_different_path_detected": "same_text_path_required",
        "suspect_copy_without_independence_detected": "suspect_copy_required",
        "not_duplicate_detected": "not_duplicate_required",
        "duplicate_not_corroboration": "duplicate_corroboration_boundary",
        "many_copies_not_many_sources": "copy_count_boundary",
        "same_text_different_path_not_independent": "same_text_independence_boundary",
        "exact_duplicate_not_deletion": "duplicate_deletion_boundary",
        "duplicate_detection_not_truth": "duplicate_truth_boundary",
        "duplicate_detection_not_authority": "duplicate_authority_boundary",
        "no_auto_merge": "auto_merge_forbidden",
        "no_old_proof_mutation": "old_proof_mutation_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tools_actions_live_effects": "effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_duplicate_hashes": "replay_duplicate_hashes_required",
        "replay_preserves_manifest_hash": "replay_manifest_hash_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "duplicate_treated_as_corroboration",
        "many_copies_treated_as_many_sources",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "old_proof_mutated",
        "auto_merge_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_sqp2_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp0_green": "sqp0_required",
        "sqp1_green": "sqp1_required",
        "quality_feature_records_written": "feature_records_required",
        "quality_scores_written": "quality_scores_required",
        "quality_policy_written": "quality_policy_required",
        "all_feature_categories_exercised": "feature_categories_required",
        "all_score_bands_exercised": "score_bands_required",
        "source_quality_not_truth": "quality_truth_boundary",
        "high_score_not_certainty": "high_score_certainty_boundary",
        "low_score_not_false": "low_score_false_boundary",
        "blocked_not_deletion": "blocked_deletion_boundary",
        "score_cannot_authorize_action": "action_authority_boundary",
        "score_cannot_authorize_tools": "tool_authority_boundary",
        "score_cannot_promote_belief": "belief_promotion_boundary",
        "score_cannot_override_operator_review": "operator_review_override_boundary",
        "score_cannot_hide_contradictions": "contradiction_visibility_boundary",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_quality_hashes": "quality_replay_required",
        "replay_preserves_manifest_hash": "manifest_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "duplicate_treated_as_corroboration",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "high_score_is_certainty",
        "low_score_is_false",
        "blocked_is_deletion",
        "score_authorizes_action",
        "score_authorizes_tools",
        "score_promotes_belief",
        "score_overrides_operator_review",
        "score_hides_contradictions",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_sqp3_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp0_green": "sqp0_required",
        "sqp1_green": "sqp1_required",
        "sqp2_green": "sqp2_required",
        "source_manifests_consumed": "source_manifests_required",
        "evidence_receipts_consumed": "evidence_receipts_required",
        "claim_links_consumed": "claim_links_required",
        "reviewed_links_consumed": "reviewed_links_required",
        "promotion_requests_consumed": "promotion_requests_required",
        "belief_revisions_consumed": "belief_revisions_required",
        "fingerprints_consumed": "fingerprints_required",
        "quality_scores_consumed": "quality_scores_required",
        "provenance_nodes_written": "provenance_nodes_required",
        "provenance_edges_written": "provenance_edges_required",
        "provenance_graph_written": "provenance_graph_required",
        "all_node_types_present": "node_types_required",
        "all_edge_types_present": "edge_types_required",
        "lineage_complete": "lineage_complete_required",
        "provenance_not_authority": "provenance_authority_boundary",
        "graph_path_not_proof": "graph_proof_boundary",
        "lineage_not_truth": "lineage_truth_boundary",
        "duplicate_not_corroboration": "duplicate_corroboration_boundary",
        "many_copies_not_many_sources": "copy_count_boundary",
        "graph_cannot_authorize_action": "graph_action_boundary",
        "graph_cannot_authorize_tools": "graph_tool_boundary",
        "graph_cannot_promote_belief": "graph_belief_promotion_boundary",
        "old_records_preserved": "old_records_required",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_node_hashes": "node_replay_required",
        "replay_preserves_edge_hashes": "edge_replay_required",
        "replay_preserves_graph_hash": "graph_replay_required",
        "replay_preserves_manifest_hash": "manifest_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "lineage_treated_as_truth",
        "graph_path_is_proof",
        "duplicate_treated_as_corroboration",
        "many_copies_treated_as_many_sources",
        "graph_authorizes_action",
        "graph_authorizes_tools",
        "graph_promotes_belief",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "old_proof_mutated",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_sqp4_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp0_green": "sqp0_required",
        "sqp3_green": "sqp3_required",
        "provenance_graph_consumed": "provenance_graph_required",
        "quality_scores_consumed": "quality_scores_required",
        "duplicate_records_consumed": "duplicate_records_required",
        "reviewed_revisions_consumed": "reviewed_revisions_required",
        "retraction_quarantine_consumed": "retraction_quarantine_required",
        "staleness_records_written": "staleness_records_required",
        "conflict_records_written": "conflict_records_required",
        "conflict_clusters_written": "conflict_clusters_required",
        "all_staleness_classes_present": "staleness_classes_required",
        "all_conflict_classes_present": "conflict_classes_required",
        "stale_not_false": "stale_false_boundary",
        "conflict_not_truth_resolution": "conflict_truth_boundary",
        "conflict_not_deletion": "conflict_deletion_boundary",
        "conflict_cannot_authorize_action": "conflict_action_boundary",
        "conflict_cannot_authorize_tools": "conflict_tool_boundary",
        "staleness_emits_review_hint_only": "staleness_hint_only_boundary",
        "contradiction_remains_visible": "contradiction_visibility_boundary",
        "source_preserved": "source_preservation_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_staleness_hashes": "staleness_replay_required",
        "replay_preserves_conflict_hashes": "conflict_replay_required",
        "replay_preserves_cluster_hashes": "cluster_replay_required",
        "replay_preserves_manifest_hash": "manifest_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "stale_source_treated_as_false",
        "conflict_resolves_truth",
        "conflict_is_deletion",
        "conflict_authorizes_action",
        "conflict_authorizes_tools",
        "duplicate_treated_as_corroboration",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_sqp5_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp2_green": "sqp2_required",
        "sqp3_green": "sqp3_required",
        "sqp4_green": "sqp4_required",
        "quality_scores_consumed": "quality_scores_required",
        "provenance_graph_consumed": "provenance_graph_required",
        "staleness_conflict_consumed": "staleness_conflict_required",
        "ais_signals_consumed": "ais_signals_required",
        "review_ledger_consumed": "review_ledger_required",
        "review_hints_written": "review_hints_required",
        "review_priority_records_written": "review_priority_required",
        "blocked_review_hints_written": "blocked_hints_required",
        "all_hint_types_present": "hint_types_required",
        "all_priority_bands_present": "priority_bands_required",
        "review_hint_not_operator_approval": "hint_approval_boundary",
        "review_hint_not_promotion": "hint_promotion_boundary",
        "review_hint_not_action": "hint_action_boundary",
        "review_hint_not_truth": "hint_truth_boundary",
        "hint_cannot_override_fever": "hint_fever_boundary",
        "hint_cannot_override_quarantine": "hint_quarantine_boundary",
        "hint_cannot_authorize_tools": "hint_tool_boundary",
        "hint_cannot_delete": "hint_deletion_boundary",
        "fever_never_unlocks": "fever_unlock_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_hint_hashes": "hint_replay_required",
        "replay_preserves_priority_hashes": "priority_replay_required",
        "replay_preserves_blocked_hashes": "blocked_replay_required",
        "replay_preserves_manifest_hash": "manifest_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "review_hint_treated_as_operator_approval",
        "hint_is_promotion",
        "hint_is_action",
        "hint_is_truth",
        "hint_overrides_fever_restriction",
        "hint_overrides_quarantine",
        "hint_authorizes_tools",
        "hint_deletes_source",
        "restriction_relaxed",
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}
