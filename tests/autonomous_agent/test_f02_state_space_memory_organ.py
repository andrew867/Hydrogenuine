"""F02 state-space memory organ tests.

Memory is not truth. Recall is not authority. State estimate is not permission.
Compressed memory is lossy. Repair recommendation is not patch approval.
"""

from __future__ import annotations

import pytest

from hg_runtime.state_space_memory.artifact_writer import (
    build_state_space_artifacts, secret_scan,
)
from hg_runtime.state_space_memory.fixtures import (
    fixture_compressed_trajectory,
    fixture_contradictory_snapshots,
    fixture_degrading_run_snapshots,
    fixture_lossy_compression,
    fixture_memory_status_snapshot,
    fixture_patch_application_attempt,
    fixture_phase19_laundering_attempt,
    fixture_phase24_laundering_attempt,
    fixture_repair_recommendation,
    fixture_secret_material_snapshot,
    fixture_stable_run_snapshots,
    fixture_stale_snapshot,
    fixture_state_query,
    fixture_state_snapshot,
    fixture_state_transition,
    fixture_tool_auth_recommendation,
)
from hg_runtime.state_space_memory.gate import validate_f02_gate
from hg_runtime.state_space_memory.organ import (
    create_repair_recommendation,
    detect_contradiction,
    detect_degradation,
    detect_stale,
    validate_compressed_trajectory,
    validate_query,
    validate_repair_recommendation,
    validate_snapshot,
    validate_transition,
    verify_hash_chain,
)
from hg_runtime.state_space_memory.replay import replay_state_space_artifacts
from hg_runtime.state_space_memory.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    StateSpaceMemoryError, reject_memory_overreach,
)


# --- schema invariants ---

def test_f02_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "F02" in VERDICT_GREEN

def test_f02_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_f02_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_f02_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


# --- snapshot tests ---

def test_f02_creates_state_snapshot():
    s = fixture_state_snapshot()
    assert s["snapshot_id"] == "snap-001"
    assert s["is_truth"] is False
    assert s["is_authority"] is False
    assert "state_hash" in s

def test_f02_state_estimate_is_not_truth():
    s = fixture_state_snapshot()
    assert s["is_truth"] is False
    assert validate_snapshot(s) == []


# --- transition tests ---

def test_f02_creates_state_transition():
    t = fixture_state_transition()
    assert t["transition_id"] == "trans-001-002"
    assert t["previous_state_hash"]
    assert t["next_state_hash"]
    assert validate_transition(t) == []

def test_f02_hash_chains_transitions():
    t1 = fixture_state_transition(1, 2)
    t2 = fixture_state_transition(2, 3)
    t2["previous_state_hash"] = t1["next_state_hash"]
    assert verify_hash_chain([t1, t2]) is True

def test_f02_hash_chain_detects_break():
    t1 = fixture_state_transition(1, 2)
    t2 = fixture_state_transition(2, 3)
    t2["previous_state_hash"] = "broken"
    assert verify_hash_chain([t1, t2]) is False


# --- compressed trajectory tests ---

def test_f02_creates_compressed_trajectory():
    t = fixture_compressed_trajectory()
    assert t["trajectory_id"]
    assert t["compression_loss_declared"] is True
    assert validate_compressed_trajectory(t) == []

def test_f02_declares_compression_loss():
    t = fixture_lossy_compression()
    assert t["compression_loss_declared"] is True
    assert len(t["dropped_detail"]) > 0


# --- degradation/stale/contradiction ---

def test_f02_marks_degrading_state():
    snaps = fixture_degrading_run_snapshots()
    assert detect_degradation(snaps) is True

def test_f02_stable_not_degrading():
    snaps = fixture_stable_run_snapshots()
    assert detect_degradation(snaps) is False

def test_f02_marks_stale_state():
    s = fixture_stale_snapshot()
    assert detect_stale(s, "2026-06-22T12:00:00Z") is True

def test_f02_records_contradiction_without_truth_adjudication():
    a, b = fixture_contradictory_snapshots()
    result = detect_contradiction(a, b)
    assert result is not None
    assert result["contradiction"] is True
    assert result["truth_adjudicated"] is False


# --- repair recommendation tests ---

def test_f02_creates_repair_recommendation():
    r = fixture_repair_recommendation()
    assert r["recommendation_id"]
    assert r["operator_review_required"] is True
    assert validate_repair_recommendation(r) == []

def test_f02_repair_recommendation_requires_operator_review():
    r = fixture_repair_recommendation()
    assert r["operator_review_required"] is True

def test_f02_repair_recommendation_is_not_permission():
    r = fixture_repair_recommendation()
    assert r["is_permission"] is False
    assert r["is_patch_approval"] is False
    assert r["authorizes_tools"] is False

def test_f02_repair_recommendation_does_not_authorize_tools():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach(fixture_tool_auth_recommendation())

def test_f02_repair_recommendation_does_not_apply_patch():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach(fixture_patch_application_attempt())

def test_f02_create_recommendation_always_advisory():
    r = create_repair_recommendation(["snap-001"], "soak", "inspect", 0.5)
    assert r["operator_review_required"] is True
    assert r["is_permission"] is False
    assert r["is_patch_approval"] is False
    assert r["authorizes_tools"] is False


# --- boundary rejection tests ---

def test_f02_recall_is_not_authority():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"recall_is_authority": True})

def test_f02_state_prediction_is_not_permission():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"state_prediction_is_permission": True})

def test_f02_memory_cannot_mutate_authority():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"memory_mutates_authority": True})

def test_f02_memory_cannot_mark_phase19_green():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach(fixture_phase19_laundering_attempt())

def test_f02_memory_cannot_mark_phase24_full_overnight_green():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach(fixture_phase24_laundering_attempt())

def test_f02_memory_cannot_enable_live_provider():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"memory_enables_live_provider": True})

def test_f02_memory_cannot_create_live_effect():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"memory_creates_live_effect": True})

def test_f02_memory_cannot_touch_hg_local():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"memory_touches_hg_local": True})

def test_f02_reject_clean():
    reject_memory_overreach({"advisory_only": True})

def test_f02_reject_agi():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"claims_agi": True})


# --- query tests ---

def test_f02_query_is_bounded():
    q = fixture_state_query()
    assert q["max_results"] == 10
    assert validate_query(q) == []

def test_f02_query_does_not_authorize_actions():
    q = fixture_state_query()
    assert q["authorizes_actions"] is False


# --- artifact / replay tests ---

def test_f02_build_artifacts():
    snaps = fixture_stable_run_snapshots()
    trans = [fixture_state_transition(1, 2), fixture_state_transition(2, 3)]
    arts = build_state_space_artifacts(
        snaps, trans,
        [fixture_compressed_trajectory()],
        [fixture_repair_recommendation()],
        [fixture_state_query()],
    )
    assert arts["all_snapshots_valid"] is True
    assert arts["all_transitions_valid"] is True
    assert arts["all_trajectories_valid"] is True
    assert arts["all_recommendations_valid"] is True
    assert arts["all_queries_valid"] is True
    assert arts["no_truth_elevation"] is True
    assert arts["no_authority_elevation"] is True
    assert arts["compression_loss_declared"] is True
    assert "artifact_hash" in arts

def test_f02_replay_preserves_hashes():
    a = replay_state_space_artifacts()
    b = replay_state_space_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def test_f02_replay_rejects_mutation():
    arts = replay_state_space_artifacts()
    original_hash = arts["artifact_hash"]
    arts["snapshot_count"] = 999
    from hg_runtime.state_space_memory.artifact_writer import _stable_hash
    assert _stable_hash(arts) != original_hash

def test_f02_no_secret_material_in_artifacts():
    snaps = fixture_stable_run_snapshots()
    trans = [fixture_state_transition(1, 2)]
    arts = build_state_space_artifacts(
        snaps, trans,
        [fixture_compressed_trajectory()],
        [fixture_repair_recommendation()],
        [fixture_state_query()],
    )
    assert secret_scan(arts) == []

def test_f02_secret_scan_detects_secret():
    s = fixture_secret_material_snapshot()
    snaps = [s]
    trans = []
    arts = build_state_space_artifacts(snaps, trans, [], [], [])
    hits = secret_scan(arts)
    assert len(hits) > 0

def test_f02_fake_green_rejected():
    with pytest.raises(StateSpaceMemoryError):
        reject_memory_overreach({"state_estimate_is_truth": True})


# --- gate tests ---

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "snapshots_exist": True, "transitions_exist": True,
        "compressed_trajectory_exists": True, "repair_recommendations_exist": True,
        "compression_loss_declared": True, "state_estimate_non_truth": True,
        "recall_non_authority": True, "recommendations_non_permission": True,
        "recommendations_non_patch_approval": True,
        "no_tool_authorization": True, "no_patch_application": True,
        "no_authority_mutation": True, "hash_chain_valid": True,
        "replay_preserves_artifact_hash": True,
        "reject_memory_overreach_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True, "report_present": True,
        "fake_green_rejected": True, "secret_scan_clean": True,
        "state_estimate_is_truth": False, "memory_is_evidence": False,
        "recall_is_authority": False, "state_prediction_is_permission": False,
        "recommendation_is_permission": False,
        "recommendation_is_patch_approval": False,
        "recommendation_authorizes_tools": False,
        "query_authorizes_actions": False, "memory_mutates_authority": False,
        "memory_marks_phase19_green": False,
        "memory_marks_phase24_full_overnight_green": False,
        "memory_enables_live_provider": False,
        "memory_creates_live_effect": False,
        "memory_touches_hg_local": False, "memory_applies_patch": False,
        "agi_claimed": False, "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_f02_gate_green():
    assert validate_f02_gate(_gate())["ok"] is True

def test_f02_gate_requires_snapshots():
    assert validate_f02_gate(_gate(snapshots_exist=False))["ok"] is False

def test_f02_gate_requires_transitions():
    assert validate_f02_gate(_gate(transitions_exist=False))["ok"] is False

def test_f02_gate_requires_compressed_trajectory():
    assert validate_f02_gate(_gate(compressed_trajectory_exists=False))["ok"] is False

def test_f02_gate_requires_recommendation_boundary():
    assert validate_f02_gate(_gate(recommendations_non_permission=False))["ok"] is False

def test_f02_gate_refuses_truth_elevation():
    assert validate_f02_gate(_gate(state_estimate_is_truth=True))["ok"] is False

def test_f02_gate_refuses_authority_elevation():
    assert validate_f02_gate(_gate(recall_is_authority=True))["ok"] is False

def test_f02_gate_refuses_tool_authorization():
    assert validate_f02_gate(_gate(recommendation_authorizes_tools=True))["ok"] is False

def test_f02_gate_refuses_patch_application():
    assert validate_f02_gate(_gate(memory_applies_patch=True))["ok"] is False

def test_f02_gate_refuses_phase19_laundering():
    assert validate_f02_gate(_gate(memory_marks_phase19_green=True))["ok"] is False

def test_f02_gate_refuses_phase24_laundering():
    assert validate_f02_gate(_gate(memory_marks_phase24_full_overnight_green=True))["ok"] is False

def test_f02_gate_refuses_live_effects():
    assert validate_f02_gate(_gate(memory_creates_live_effect=True))["ok"] is False

def test_f02_gate_refuses_missing_replay():
    assert validate_f02_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False
