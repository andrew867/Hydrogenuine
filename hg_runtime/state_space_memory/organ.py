"""F02 state-space memory organ domain logic."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.state_space_memory.schemas import (
    StateSpaceMemoryError,
    reject_memory_overreach,
)


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def validate_snapshot(snap: dict) -> list[str]:
    issues = []
    if not snap.get("snapshot_id"):
        issues.append("missing_snapshot_id")
    if snap.get("is_truth"):
        issues.append("snapshot_must_not_be_truth")
    if snap.get("is_authority"):
        issues.append("snapshot_must_not_be_authority")
    if "uncertainty_score" not in snap:
        issues.append("missing_uncertainty_score")
    reject_memory_overreach(snap)
    return issues


def validate_transition(trans: dict) -> list[str]:
    issues = []
    if not trans.get("transition_id"):
        issues.append("missing_transition_id")
    if not trans.get("previous_state_hash"):
        issues.append("missing_previous_hash")
    if not trans.get("next_state_hash"):
        issues.append("missing_next_hash")
    return issues


def verify_hash_chain(transitions: list[dict]) -> bool:
    for i in range(1, len(transitions)):
        if transitions[i]["previous_state_hash"] != transitions[i - 1]["next_state_hash"]:
            return False
    return True


def detect_degradation(snapshots: list[dict]) -> bool:
    if len(snapshots) < 2:
        return False
    scores = [s.get("uncertainty_score", 0) for s in snapshots]
    return scores[-1] > scores[0] + 0.1


def detect_stale(snapshot: dict, current_timestamp: str) -> bool:
    snap_ts = snapshot.get("timestamp", "")
    return snap_ts < current_timestamp[:10]


def detect_contradiction(snap_a: dict, snap_b: dict) -> dict | None:
    if snap_a.get("sequence") != snap_b.get("sequence"):
        return None
    if snap_a.get("state_hash") != snap_b.get("state_hash"):
        return {
            "contradiction": True,
            "sequence": snap_a.get("sequence"),
            "hash_a": snap_a.get("state_hash"),
            "hash_b": snap_b.get("state_hash"),
            "truth_adjudicated": False,
        }
    return None


def validate_compressed_trajectory(traj: dict) -> list[str]:
    issues = []
    if not traj.get("trajectory_id"):
        issues.append("missing_trajectory_id")
    if not traj.get("compression_loss_declared"):
        issues.append("compression_loss_must_be_declared")
    return issues


def validate_repair_recommendation(rec: dict) -> list[str]:
    issues = []
    if not rec.get("recommendation_id"):
        issues.append("missing_recommendation_id")
    if not rec.get("operator_review_required"):
        issues.append("operator_review_must_be_required")
    if rec.get("is_permission"):
        issues.append("recommendation_must_not_be_permission")
    if rec.get("is_patch_approval"):
        issues.append("recommendation_must_not_be_patch_approval")
    if rec.get("authorizes_tools"):
        issues.append("recommendation_must_not_authorize_tools")
    return issues


def validate_query(query: dict) -> list[str]:
    issues = []
    if not query.get("query_id"):
        issues.append("missing_query_id")
    if query.get("is_truth"):
        issues.append("query_must_not_be_truth")
    if query.get("is_authority"):
        issues.append("query_must_not_be_authority")
    if query.get("authorizes_actions"):
        issues.append("query_must_not_authorize_actions")
    max_results = query.get("max_results", 0)
    if max_results <= 0 or max_results > 1000:
        issues.append("max_results_must_be_bounded")
    return issues


def create_repair_recommendation(
    source_observations: list[str],
    affected_subsystem: str,
    recommended_action: str,
    confidence: float,
) -> dict:
    return {
        "recommendation_id": f"rec-{_hash(source_observations)}",
        "source_observations": source_observations,
        "affected_subsystem": affected_subsystem,
        "recommended_action": recommended_action,
        "evidence_links": [],
        "confidence": confidence,
        "uncertainty": 1.0 - confidence,
        "risk": "medium" if confidence < 0.7 else "low",
        "operator_review_required": True,
        "is_permission": False,
        "is_patch_approval": False,
        "authorizes_tools": False,
    }
