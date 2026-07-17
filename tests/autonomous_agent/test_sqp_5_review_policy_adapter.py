"""SQP-5 review policy adapter tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.restriction_policy import unlock_actions_for_level
from hg_runtime.source_quality_provenance.gate import validate_sqp5_gate
from hg_runtime.source_quality_provenance.redaction import secret_scan
from hg_runtime.source_quality_provenance.review_hint_builder import build_review_hint
from hg_runtime.source_quality_provenance.review_hint_replay import replay_review_policy_adapter
from hg_runtime.source_quality_provenance.review_policy_adapter import (
    build_review_policy_adapter_layer,
    build_sqp5_inputs,
    classify_hint,
)
from hg_runtime.source_quality_provenance.review_priority import priority_for_hint
from hg_runtime.source_quality_provenance.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    REVIEW_HINT_TYPES,
    REVIEW_PRIORITY_BANDS,
    SQPBoundaryError,
)


def _layer():
    return build_review_policy_adapter_layer(build_sqp5_inputs())


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SQP_5_REVIEW_POLICY_ADAPTER",
        "reviewed_beta_green": True,
        "sqp2_green": True,
        "sqp3_green": True,
        "sqp4_green": True,
        "quality_scores_consumed": True,
        "provenance_graph_consumed": True,
        "staleness_conflict_consumed": True,
        "ais_signals_consumed": True,
        "review_ledger_consumed": True,
        "review_hints_written": True,
        "review_priority_records_written": True,
        "blocked_review_hints_written": True,
        "all_hint_types_present": True,
        "all_priority_bands_present": True,
        "review_hint_not_operator_approval": True,
        "review_hint_not_promotion": True,
        "review_hint_not_action": True,
        "review_hint_not_truth": True,
        "hint_cannot_override_fever": True,
        "hint_cannot_override_quarantine": True,
        "hint_cannot_authorize_tools": True,
        "hint_cannot_delete": True,
        "fever_never_unlocks": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_hint_hashes": True,
        "replay_preserves_priority_hashes": True,
        "replay_preserves_blocked_hashes": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Classification --------------------------------------------------------

def test_sqp5_classify_hint():
    assert classify_hint({"security_finding": True}) == "BLOCK_PROMOTION_REQUEST"
    assert classify_hint({"retraction_conflict": True}) == "RETRACTION_RECOMMENDED"
    assert classify_hint({"quarantined": True}) == "QUARANTINE_RECOMMENDED"
    assert classify_hint({"stale_by_policy": True}) == "REQUIRE_OPERATOR_CONFIRMATION"
    assert classify_hint({"conflict": True}) == "PRIORITIZE_REVIEW"
    assert classify_hint({"single_source": True}) == "REQUIRE_SECOND_SOURCE"
    assert classify_hint({"low_quality": True}) == "REQUEST_MORE_EVIDENCE"
    assert classify_hint({}) == "ALLOW_PROVISIONAL_REVIEW"


def test_sqp5_priority_mapping():
    assert priority_for_hint("BLOCK_PROMOTION_REQUEST") == "CRITICAL_REVIEW_REQUIRED"
    assert priority_for_hint("PRIORITIZE_REVIEW") == "HIGH"
    assert priority_for_hint("REQUEST_MORE_EVIDENCE") == "NORMAL"
    assert priority_for_hint("ALLOW_PROVISIONAL_REVIEW") == "LOW"


def test_sqp5_hint_builder_rejects_unknown_type():
    with pytest.raises(SQPBoundaryError):
        build_review_hint(hint_id="h", source_id="s", hint_type="NOPE", priority="LOW", rationale=[])


def test_sqp5_hint_builder_rejects_unknown_priority():
    with pytest.raises(SQPBoundaryError):
        build_review_hint(hint_id="h", source_id="s", hint_type="PRIORITIZE_REVIEW", priority="URGENT", rationale=[])


# --- Coverage --------------------------------------------------------------

def test_sqp5_all_hint_types_present():
    m = _layer()["manifest"]
    assert REVIEW_HINT_TYPES <= set(m["hint_types_including_blocked"])


def test_sqp5_all_priority_bands_present():
    m = _layer()["manifest"]
    assert REVIEW_PRIORITY_BANDS <= set(m["priority_bands_present"])


# --- Restriction-respecting blocking ---------------------------------------

def test_sqp5_permissive_hint_blocked_under_restriction():
    blocked = _layer()["blocked_hints"]
    assert blocked
    for b in blocked:
        assert b["requested_hint_type"] == "ALLOW_PROVISIONAL_REVIEW"
        assert b["replacement_hint_type"] == "REQUIRE_OPERATOR_CONFIRMATION"
        assert b["hint_overrides_fever_restriction"] is False
        assert b["hint_overrides_quarantine"] is False
        assert b["restriction_relaxed"] is False


def test_sqp5_fevered_clean_source_does_not_get_provisional_review():
    hints = {h["source_id"]: h for h in _layer()["hints"]}
    # Clean-but-fevered source must NOT receive the permissive hint.
    assert hints["sqp5-source-fevered"]["hint_type"] == "REQUIRE_OPERATOR_CONFIRMATION"
    # A truly clean (NORMAL) source may.
    assert hints["sqp5-source-clean"]["hint_type"] == "ALLOW_PROVISIONAL_REVIEW"


def test_sqp5_fever_never_unlocks():
    assert _layer()["manifest"]["fever_never_unlocks"] is True
    assert unlock_actions_for_level("RED_FEVER") == []


def test_sqp5_hints_are_non_authoritative():
    for h in _layer()["hints"]:
        assert h["review_hint_treated_as_operator_approval"] is False
        assert h["hint_is_promotion"] is False
        assert h["hint_is_action"] is False
        assert h["hint_is_truth"] is False
        assert h["hint_overrides_fever_restriction"] is False
        assert h["hint_overrides_quarantine"] is False
        assert h["hint_authorizes_tools"] is False
        assert h["hint_deletes_source"] is False


# --- Replay ----------------------------------------------------------------

def test_sqp5_replay_preserves_hashes():
    layer = _layer()
    inputs = build_sqp5_inputs()
    replay = replay_review_policy_adapter(
        inputs,
        [h["record_hash"] for h in layer["hints"]],
        [p["record_hash"] for p in layer["priorities"]],
        [b["record_hash"] for b in layer["blocked_hints"]],
        layer["manifest"]["manifest_hash"],
    )
    assert replay["replay_preserves_hint_hashes"] is True
    assert replay["replay_preserves_priority_hashes"] is True
    assert replay["replay_preserves_blocked_hashes"] is True
    assert replay["replay_preserves_manifest_hash"] is True


def test_sqp5_replay_rejects_mutation():
    replay = replay_review_policy_adapter(build_sqp5_inputs(), ["mutated"], ["mutated"], ["mutated"], "mutated")
    assert replay["replay_preserves_manifest_hash"] is False


def test_sqp5_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_sqp5_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_sqp5_gate_passes_full_summary():
    assert validate_sqp5_gate(_summary())["ok"] is True


def test_sqp5_gate_refuses_hint_as_operator_approval():
    assert validate_sqp5_gate(_summary(review_hint_treated_as_operator_approval=True))["ok"] is False


def test_sqp5_gate_refuses_hint_as_promotion_or_action():
    assert validate_sqp5_gate(_summary(hint_is_promotion=True))["ok"] is False
    assert validate_sqp5_gate(_summary(hint_is_action=True))["ok"] is False


def test_sqp5_gate_refuses_hint_overriding_fever_or_quarantine():
    assert validate_sqp5_gate(_summary(hint_overrides_fever_restriction=True))["ok"] is False
    assert validate_sqp5_gate(_summary(hint_overrides_quarantine=True))["ok"] is False


def test_sqp5_gate_refuses_restriction_relaxed():
    assert validate_sqp5_gate(_summary(restriction_relaxed=True))["ok"] is False


def test_sqp5_gate_refuses_missing_coverage():
    assert validate_sqp5_gate(_summary(all_hint_types_present=False))["ok"] is False
    assert validate_sqp5_gate(_summary(all_priority_bands_present=False))["ok"] is False


def test_sqp5_gate_refuses_web_provider_or_live_effects():
    assert validate_sqp5_gate(_summary(web_browse_performed=True))["ok"] is False
    assert validate_sqp5_gate(_summary(external_provider_calls_made=True))["ok"] is False
    assert validate_sqp5_gate(_summary(live_external_side_effects_created=True))["ok"] is False
