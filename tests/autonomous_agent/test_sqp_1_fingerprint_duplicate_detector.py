"""SQP-1 fingerprint and duplicate detector tests."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.duplicate_detector import classify_duplicate
from hg_runtime.source_quality_provenance.duplicate_replay import replay_duplicate_detection
from hg_runtime.source_quality_provenance.fixtures import build_sqp1_duplicate_fixture_records
from hg_runtime.source_quality_provenance.gate import validate_sqp1_gate
from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.redaction import secret_scan
from hg_runtime.source_quality_provenance.schemas import DUPLICATE_CLASSES, PHASE19_VERDICT, PHASE24_STATUS


def _records():
    return build_sqp1_duplicate_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SQP_1_FINGERPRINT_DUPLICATE_DETECTOR",
        "reviewed_beta_green": True,
        "sqp0_green": True,
        "source_manifests_consumed": True,
        "evidence_receipts_consumed": True,
        "reviewed_links_consumed": True,
        "source_identities_written": True,
        "source_fingerprints_written": True,
        "duplicate_records_written": True,
        "all_duplicate_classes_exercised": True,
        "exact_duplicate_detected": True,
        "normalized_duplicate_detected": True,
        "same_source_different_excerpt_detected": True,
        "same_text_different_path_detected": True,
        "suspect_copy_without_independence_detected": True,
        "not_duplicate_detected": True,
        "duplicate_not_corroboration": True,
        "many_copies_not_many_sources": True,
        "same_text_different_path_not_independent": True,
        "exact_duplicate_not_deletion": True,
        "duplicate_detection_not_truth": True,
        "duplicate_detection_not_authority": True,
        "no_auto_merge": True,
        "no_old_proof_mutation": True,
        "no_belief_promotion": True,
        "no_tools_actions_live_effects": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_duplicate_hashes": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_sqp1_builds_source_identities_and_fingerprints():
    records = _records()
    assert len(records["source_identity_records"]) == len(records["sources"])
    assert len(records["source_fingerprints"]) == len(records["sources"])
    assert all(row["record_type"] == "source_fingerprint_v1" for row in records["source_fingerprints"])


def test_sqp1_exercises_all_duplicate_classes():
    classes = {row["duplicate_class"] for row in _records()["duplicate_source_records"]}
    assert DUPLICATE_CLASSES <= classes


def test_sqp1_classifies_exact_duplicate():
    records = _records()["source_fingerprints"]
    assert classify_duplicate(records[0], records[1]) == "EXACT_CONTENT_DUPLICATE"


def test_sqp1_classifies_same_source_different_excerpt():
    records = _records()["source_fingerprints"]
    assert classify_duplicate(records[0], records[2]) == "SAME_SOURCE_DIFFERENT_EXCERPT"


def test_sqp1_classifies_normalized_duplicate():
    records = _records()["source_fingerprints"]
    assert classify_duplicate(records[0], records[3]) == "NORMALIZED_TEXT_DUPLICATE"


def test_sqp1_classifies_same_text_different_path():
    records = _records()["source_fingerprints"]
    assert classify_duplicate(records[0], records[4]) == "SAME_TEXT_DIFFERENT_PATH"


def test_sqp1_classifies_suspect_copy_without_independence():
    records = _records()["source_fingerprints"]
    assert classify_duplicate(records[0], records[5]) == "SUSPECT_COPY_WITHOUT_INDEPENDENCE"


def test_sqp1_classifies_not_duplicate():
    records = _records()["source_fingerprints"]
    assert classify_duplicate(records[0], records[6]) == "NOT_DUPLICATE"


def test_sqp1_duplicate_is_not_corroboration():
    assert all(not row["duplicate_treated_as_corroboration"] for row in _records()["duplicate_source_records"])


def test_sqp1_many_copies_are_not_many_sources():
    assert all(not row["many_copies_treated_as_many_sources"] for row in _records()["duplicate_source_records"])


def test_sqp1_same_text_different_path_is_not_independent():
    records = [row for row in _records()["duplicate_source_records"] if row["duplicate_class"] == "SAME_TEXT_DIFFERENT_PATH"]
    assert records
    assert all(row["independent_corroboration_count"] == 1 for row in records)


def test_sqp1_exact_duplicate_is_not_deletion_permission():
    records = [row for row in _records()["duplicate_source_records"] if row["duplicate_class"] == "EXACT_CONTENT_DUPLICATE"]
    assert records
    assert all(not row["deletion_performed"] for row in records)


def test_sqp1_detection_not_truth_or_authority():
    rows = _records()["duplicate_source_records"]
    assert all(not row["truth_claimed"] for row in rows)
    assert all(not row["authority_granted"] for row in rows)


def test_sqp1_detection_cannot_auto_merge_or_mutate_old_proofs():
    rows = _records()["duplicate_source_records"]
    assert all(not row["auto_merge_performed"] for row in rows)
    assert all(not row["old_proof_mutated"] for row in rows)


def test_sqp1_no_belief_promotion_tools_actions_live_effects():
    rows = _records()["duplicate_source_records"]
    assert all(not row["belief_promotion_automatic"] for row in rows)
    assert all(not row["tools_authorized"] for row in rows)
    assert all(not row["live_external_side_effects_created"] for row in rows)
    assert all(not row["patch_request_applied"] for row in rows)


def test_sqp1_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_sqp1_replay_preserves_duplicate_hashes():
    records = _records()
    expected_hashes = [row["record_hash"] for row in records["duplicate_source_records"]]
    manifest_hash = record_hash(
        {
            "fingerprints": records["source_fingerprints"],
            "duplicate_records": records["duplicate_source_records"],
        }
    )
    replay = replay_duplicate_detection(records["sources"], manifest_hash, expected_hashes)
    assert replay["replay_preserves_duplicate_hashes"] is True
    assert replay["replay_preserves_manifest_hash"] is True


def test_sqp1_replay_rejects_mutated_duplicate_hash():
    records = _records()
    replay = replay_duplicate_detection(records["sources"], "mutated", ["mutated"])
    assert replay["replay_preserves_duplicate_hashes"] is False
    assert replay["replay_preserves_manifest_hash"] is False


def test_sqp1_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_sqp1_gate_passes_full_summary():
    assert validate_sqp1_gate(_summary())["ok"] is True


def test_sqp1_gate_refuses_missing_reviewed_beta():
    assert validate_sqp1_gate(_summary(reviewed_beta_green=False))["ok"] is False


def test_sqp1_gate_refuses_duplicate_as_corroboration():
    assert validate_sqp1_gate(_summary(duplicate_treated_as_corroboration=True))["ok"] is False


def test_sqp1_gate_refuses_many_copies_as_many_sources():
    assert validate_sqp1_gate(_summary(many_copies_treated_as_many_sources=True))["ok"] is False


def test_sqp1_gate_refuses_auto_merge_or_old_proof_mutation():
    assert validate_sqp1_gate(_summary(auto_merge_performed=True))["ok"] is False
    assert validate_sqp1_gate(_summary(old_proof_mutated=True))["ok"] is False


def test_sqp1_gate_refuses_belief_promotion_or_authority():
    assert validate_sqp1_gate(_summary(belief_promotion_automatic=True))["ok"] is False
    assert validate_sqp1_gate(_summary(authority_granted=True))["ok"] is False


def test_sqp1_gate_refuses_live_effects_or_provider():
    assert validate_sqp1_gate(_summary(live_external_side_effects_created=True))["ok"] is False
    assert validate_sqp1_gate(_summary(external_provider_calls_made=True))["ok"] is False
