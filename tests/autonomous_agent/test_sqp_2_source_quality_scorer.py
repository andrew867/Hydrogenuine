"""SQP-2 source quality scorer tests."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.fixtures import build_sqp2_quality_feature_sets, build_sqp2_quality_fixture_records
from hg_runtime.source_quality_provenance.gate import validate_sqp2_gate
from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.quality_policy import QUALITY_POLICY
from hg_runtime.source_quality_provenance.quality_replay import replay_quality_scoring
from hg_runtime.source_quality_provenance.quality_scorer import score_band_for_features, score_sources
from hg_runtime.source_quality_provenance.redaction import secret_scan
from hg_runtime.source_quality_provenance.schemas import PHASE19_VERDICT, PHASE24_STATUS, QUALITY_BANDS, QUALITY_FEATURE_CATEGORIES


def _records():
    return build_sqp2_quality_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SQP_2_SOURCE_QUALITY_SCORER",
        "reviewed_beta_green": True,
        "sqp0_green": True,
        "sqp1_green": True,
        "quality_feature_records_written": True,
        "quality_scores_written": True,
        "quality_policy_written": True,
        "all_feature_categories_exercised": True,
        "all_score_bands_exercised": True,
        "source_quality_not_truth": True,
        "high_score_not_certainty": True,
        "low_score_not_false": True,
        "blocked_not_deletion": True,
        "score_cannot_authorize_action": True,
        "score_cannot_authorize_tools": True,
        "score_cannot_promote_belief": True,
        "score_cannot_override_operator_review": True,
        "score_cannot_hide_contradictions": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_quality_hashes": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_sqp2_declares_quality_features_and_bands():
    assert {
        "HAS_SOURCE_IDENTITY",
        "HAS_STABLE_FINGERPRINT",
        "HAS_EXCERPT_BOUNDARY",
        "HAS_REDACTION_STATUS",
        "HAS_REVIEW_DECISION",
        "HAS_PROVENANCE_LINK",
        "DUPLICATE_COLLAPSED",
        "STALE_SIGNAL_PRESENT",
        "CONFLICT_SIGNAL_PRESENT",
        "QUARANTINE_HISTORY_PRESENT",
        "SECURITY_FINDING_PRESENT",
    } <= QUALITY_FEATURE_CATEGORIES
    assert {
        "UNRATED",
        "LOW_INFORMATION",
        "STRUCTURALLY_USABLE",
        "REVIEWED_USABLE",
        "CONFLICTED_OR_QUARANTINED",
        "BLOCKED",
    } <= QUALITY_BANDS


def test_sqp2_policy_is_non_authoritative():
    assert QUALITY_POLICY["source_quality_is_truth"] is False
    assert QUALITY_POLICY["high_score_is_certainty"] is False
    assert QUALITY_POLICY["score_authorizes_action"] is False
    assert QUALITY_POLICY["score_promotes_belief"] is False


def test_sqp2_score_band_rules():
    feature_sets = build_sqp2_quality_feature_sets()
    assert score_band_for_features(feature_sets["sqp2-source-unrated"]) == "UNRATED"
    assert score_band_for_features(feature_sets["sqp2-source-low-information"]) == "LOW_INFORMATION"
    assert score_band_for_features(feature_sets["sqp2-source-structural"]) == "STRUCTURALLY_USABLE"
    assert score_band_for_features(feature_sets["sqp2-source-reviewed"]) == "REVIEWED_USABLE"
    assert score_band_for_features(feature_sets["sqp2-source-conflicted"]) == "CONFLICTED_OR_QUARANTINED"
    assert score_band_for_features(feature_sets["sqp2-source-blocked"]) == "BLOCKED"


def test_sqp2_writes_feature_records_and_scores():
    records = _records()
    assert records["source_quality_feature_records"]
    assert records["source_quality_scores"]
    assert {row["quality_band"] for row in records["source_quality_scores"]} >= QUALITY_BANDS


def test_sqp2_exercises_all_feature_categories():
    feature_names = {
        name
        for row in _records()["source_quality_feature_records"]
        for name, present in row["features"].items()
        if present
    }
    assert QUALITY_FEATURE_CATEGORIES <= feature_names


def test_sqp2_source_quality_is_not_truth_or_certainty():
    scores = _records()["source_quality_scores"]
    assert all(not row["source_quality_treated_as_truth"] for row in scores)
    assert all(not row["high_score_is_certainty"] for row in scores)


def test_sqp2_low_score_is_not_false_and_blocked_not_deletion():
    scores = _records()["source_quality_scores"]
    assert all(not row["low_score_is_false"] for row in scores)
    assert all(not row["blocked_is_deletion"] for row in scores)
    assert all(not row["deletion_performed"] for row in scores)


def test_sqp2_score_cannot_authorize_action_or_tools():
    scores = _records()["source_quality_scores"]
    assert all(not row["score_authorizes_action"] for row in scores)
    assert all(not row["score_authorizes_tools"] for row in scores)
    assert all(not row["authority_granted"] for row in scores)
    assert all(not row["tools_authorized"] for row in scores)


def test_sqp2_score_cannot_promote_belief_or_override_review():
    scores = _records()["source_quality_scores"]
    assert all(not row["score_promotes_belief"] for row in scores)
    assert all(not row["belief_promotion_automatic"] for row in scores)
    assert all(not row["score_overrides_operator_review"] for row in scores)


def test_sqp2_score_cannot_hide_contradictions():
    assert all(not row["score_hides_contradictions"] for row in _records()["source_quality_scores"])


def test_sqp2_no_web_provider_or_live_effects():
    scores = _records()["source_quality_scores"]
    assert all(not row["web_browse_performed"] for row in scores)
    assert all(not row["external_provider_calls_made"] for row in scores)
    assert all(not row["live_external_side_effects_created"] for row in scores)


def test_sqp2_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_sqp2_replay_preserves_quality_hashes():
    feature_sets = build_sqp2_quality_feature_sets()
    scored = score_sources(feature_sets)
    manifest_hash = record_hash(scored)
    expected_hashes = [row["quality_hash"] for row in scored["source_quality_scores"]]
    replay = replay_quality_scoring(feature_sets, manifest_hash, expected_hashes)
    assert replay["replay_preserves_quality_hashes"] is True
    assert replay["replay_preserves_manifest_hash"] is True


def test_sqp2_replay_rejects_mutated_score_hash():
    replay = replay_quality_scoring(build_sqp2_quality_feature_sets(), "mutated", ["mutated"])
    assert replay["replay_preserves_quality_hashes"] is False
    assert replay["replay_preserves_manifest_hash"] is False


def test_sqp2_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_sqp2_gate_passes_full_summary():
    assert validate_sqp2_gate(_summary())["ok"] is True


def test_sqp2_gate_refuses_quality_as_truth_or_certainty():
    assert validate_sqp2_gate(_summary(source_quality_treated_as_truth=True))["ok"] is False
    assert validate_sqp2_gate(_summary(high_score_is_certainty=True))["ok"] is False


def test_sqp2_gate_refuses_low_false_or_blocked_deletion():
    assert validate_sqp2_gate(_summary(low_score_is_false=True))["ok"] is False
    assert validate_sqp2_gate(_summary(blocked_is_deletion=True))["ok"] is False


def test_sqp2_gate_refuses_action_tools_or_belief_promotion():
    assert validate_sqp2_gate(_summary(score_authorizes_action=True))["ok"] is False
    assert validate_sqp2_gate(_summary(score_authorizes_tools=True))["ok"] is False
    assert validate_sqp2_gate(_summary(score_promotes_belief=True))["ok"] is False


def test_sqp2_gate_refuses_operator_override_or_hidden_contradiction():
    assert validate_sqp2_gate(_summary(score_overrides_operator_review=True))["ok"] is False
    assert validate_sqp2_gate(_summary(score_hides_contradictions=True))["ok"] is False


def test_sqp2_gate_refuses_web_provider_or_live_effects():
    assert validate_sqp2_gate(_summary(web_browse_performed=True))["ok"] is False
    assert validate_sqp2_gate(_summary(external_provider_calls_made=True))["ok"] is False
    assert validate_sqp2_gate(_summary(live_external_side_effects_created=True))["ok"] is False
