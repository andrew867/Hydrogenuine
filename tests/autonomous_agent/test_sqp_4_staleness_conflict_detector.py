"""SQP-4 staleness and source conflict detector tests."""

from __future__ import annotations

import pytest

from hg_runtime.source_quality_provenance.conflict_policy import CONFLICT_POLICY
from hg_runtime.source_quality_provenance.conflict_replay import replay_staleness_conflict
from hg_runtime.source_quality_provenance.gate import validate_sqp4_gate
from hg_runtime.source_quality_provenance.redaction import secret_scan
from hg_runtime.source_quality_provenance.source_conflict_detector import (
    build_conflict_record,
    build_sqp4_inputs,
    build_staleness_conflict_layer,
    cluster_conflicts,
)
from hg_runtime.source_quality_provenance.staleness_detector import classify_staleness, detect_staleness
from hg_runtime.source_quality_provenance.schemas import (
    CONFLICT_CLASSES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    STALENESS_CLASSES,
    SQPBoundaryError,
)


def _layer():
    return build_staleness_conflict_layer(build_sqp4_inputs())


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SQP_4_STALENESS_CONFLICT_DETECTOR",
        "reviewed_beta_green": True,
        "sqp0_green": True,
        "sqp3_green": True,
        "provenance_graph_consumed": True,
        "quality_scores_consumed": True,
        "duplicate_records_consumed": True,
        "reviewed_revisions_consumed": True,
        "retraction_quarantine_consumed": True,
        "staleness_records_written": True,
        "conflict_records_written": True,
        "conflict_clusters_written": True,
        "all_staleness_classes_present": True,
        "all_conflict_classes_present": True,
        "stale_not_false": True,
        "conflict_not_truth_resolution": True,
        "conflict_not_deletion": True,
        "conflict_cannot_authorize_action": True,
        "conflict_cannot_authorize_tools": True,
        "staleness_emits_review_hint_only": True,
        "contradiction_remains_visible": True,
        "source_preserved": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_staleness_hashes": True,
        "replay_preserves_conflict_hashes": True,
        "replay_preserves_cluster_hashes": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Staleness -------------------------------------------------------------

def test_sqp4_staleness_classifier():
    assert classify_staleness({"source_id": "s", "age_class": "CURRENT"}) == "CURRENT_ENOUGH"
    assert classify_staleness({"source_id": "s", "age_class": None}) == "DATE_UNKNOWN"
    assert classify_staleness({"source_id": "s", "age_class": "OLD"}) == "POSSIBLY_STALE"
    assert classify_staleness({"source_id": "s", "age_class": "STALE"}) == "STALE_BY_POLICY"
    assert classify_staleness({"source_id": "s", "superseded_by_reviewed": True}) == "SUPERSEDED_BY_REVIEWED_SOURCE"
    assert classify_staleness({"source_id": "s", "retracted_or_quarantined": True}) == "RETRACTED_OR_QUARANTINED"


def test_sqp4_staleness_classifier_rejects_unknown_age():
    with pytest.raises(SQPBoundaryError):
        classify_staleness({"source_id": "s", "age_class": "ANCIENT"})


def test_sqp4_all_staleness_classes_present():
    classes = {r["staleness_class"] for r in _layer()["staleness_records"]}
    assert STALENESS_CLASSES <= classes


def test_sqp4_stale_is_not_false():
    for r in _layer()["staleness_records"]:
        assert r["stale_source_treated_as_false"] is False
        assert r["staleness_deletes_source"] is False
        assert r["source_preserved"] is True


def test_sqp4_staleness_only_suggests_review():
    for r in _layer()["staleness_records"]:
        assert r["staleness_authorizes_action"] is False
        assert r["staleness_authorizes_tools"] is False
    # Current sources need no review hint; stale/retracted/superseded may.
    by_id = {r["source_id"]: r for r in _layer()["staleness_records"]}
    assert by_id["sqp4-source-current"]["may_emit_review_hint"] is False
    assert by_id["sqp4-source-stale"]["may_emit_review_hint"] is True


# --- Conflicts -------------------------------------------------------------

def test_sqp4_conflict_builder_rejects_unknown_class():
    with pytest.raises(SQPBoundaryError):
        build_conflict_record(conflict_id="c", conflict_class="NOPE", participant_source_ids=["a"], detail_ref="x")


def test_sqp4_all_conflict_classes_present():
    classes = {r["conflict_class"] for r in _layer()["conflict_records"]}
    assert CONFLICT_CLASSES <= classes


def test_sqp4_conflict_is_not_truth_resolution_or_deletion():
    for r in _layer()["conflict_records"]:
        assert r["conflict_resolves_truth"] is False
        assert r["conflict_is_deletion"] is False
        assert r["deletion_performed"] is False
        assert r["contradiction_remains_visible"] is True
        assert r["source_preserved"] is True
        assert r["conflict_status"] == "VISIBLE_UNRESOLVED"


def test_sqp4_conflict_cannot_authorize():
    for r in _layer()["conflict_records"]:
        assert r["conflict_authorizes_action"] is False
        assert r["conflict_authorizes_tools"] is False


def test_sqp4_conflict_clusters_group_shared_sources():
    clusters = _layer()["conflict_clusters"]
    assert clusters
    # Every conflict id appears in exactly one cluster.
    all_conflict_ids = sorted(c["conflict_id"] for c in _layer()["conflict_records"])
    clustered = sorted(cid for cl in clusters for cid in cl["conflict_ids"])
    assert clustered == all_conflict_ids
    for cl in clusters:
        assert cl["conflict_resolves_truth"] is False
        assert cl["contradiction_remains_visible"] is True


def test_sqp4_cluster_merges_conflicts_sharing_a_source():
    conflicts = [
        build_conflict_record(conflict_id="c1", conflict_class="CLAIM_CONFLICT", participant_source_ids=["a", "b"], detail_ref="x"),
        build_conflict_record(conflict_id="c2", conflict_class="QUALITY_CONFLICT", participant_source_ids=["b", "c"], detail_ref="x"),
        build_conflict_record(conflict_id="c3", conflict_class="RETRACTION_CONFLICT", participant_source_ids=["d", "e"], detail_ref="x"),
    ]
    clusters = cluster_conflicts(conflicts)
    # c1+c2 share "b" -> one cluster; c3 isolated -> another.
    assert len(clusters) == 2
    sizes = sorted(len(cl["conflict_ids"]) for cl in clusters)
    assert sizes == [1, 2]


# --- Manifest / replay -----------------------------------------------------

def test_sqp4_manifest_flags_complete_class_coverage():
    m = _layer()["manifest"]
    assert m["all_staleness_classes_present"] is True
    assert m["all_conflict_classes_present"] is True


def test_sqp4_replay_preserves_hashes():
    layer = _layer()
    inputs = build_sqp4_inputs()
    replay = replay_staleness_conflict(
        inputs,
        [r["record_hash"] for r in layer["staleness_records"]],
        [r["record_hash"] for r in layer["conflict_records"]],
        [r["record_hash"] for r in layer["conflict_clusters"]],
        layer["manifest"]["manifest_hash"],
    )
    assert replay["replay_preserves_staleness_hashes"] is True
    assert replay["replay_preserves_conflict_hashes"] is True
    assert replay["replay_preserves_cluster_hashes"] is True
    assert replay["replay_preserves_manifest_hash"] is True


def test_sqp4_replay_rejects_mutation():
    replay = replay_staleness_conflict(build_sqp4_inputs(), ["mutated"], ["mutated"], ["mutated"], "mutated")
    assert replay["replay_preserves_manifest_hash"] is False


def test_sqp4_policy_is_non_authoritative():
    assert CONFLICT_POLICY["stale_is_false"] is False
    assert CONFLICT_POLICY["conflict_resolves_truth"] is False
    assert CONFLICT_POLICY["conflict_is_deletion"] is False
    assert CONFLICT_POLICY["staleness_may_emit_review_hint_only"] is True


def test_sqp4_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_sqp4_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_sqp4_gate_passes_full_summary():
    assert validate_sqp4_gate(_summary())["ok"] is True


def test_sqp4_gate_refuses_stale_as_false():
    assert validate_sqp4_gate(_summary(stale_source_treated_as_false=True))["ok"] is False


def test_sqp4_gate_refuses_conflict_as_truth_resolution():
    assert validate_sqp4_gate(_summary(conflict_resolves_truth=True))["ok"] is False


def test_sqp4_gate_refuses_conflict_as_deletion():
    assert validate_sqp4_gate(_summary(conflict_is_deletion=True))["ok"] is False
    assert validate_sqp4_gate(_summary(deletion_performed=True))["ok"] is False


def test_sqp4_gate_refuses_conflict_authorizing_action_or_tools():
    assert validate_sqp4_gate(_summary(conflict_authorizes_action=True))["ok"] is False
    assert validate_sqp4_gate(_summary(conflict_authorizes_tools=True))["ok"] is False


def test_sqp4_gate_refuses_missing_classes():
    assert validate_sqp4_gate(_summary(all_staleness_classes_present=False))["ok"] is False
    assert validate_sqp4_gate(_summary(all_conflict_classes_present=False))["ok"] is False


def test_sqp4_gate_refuses_web_provider_or_live_effects():
    assert validate_sqp4_gate(_summary(web_browse_performed=True))["ok"] is False
    assert validate_sqp4_gate(_summary(external_provider_calls_made=True))["ok"] is False
    assert validate_sqp4_gate(_summary(live_external_side_effects_created=True))["ok"] is False
