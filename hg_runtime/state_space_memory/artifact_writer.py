"""F02 state-space memory organ artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.state_space_memory.organ import (
    validate_compressed_trajectory,
    validate_query,
    validate_repair_recommendation,
    validate_snapshot,
    validate_transition,
    verify_hash_chain,
)
from hg_runtime.state_space_memory.schemas import reject_memory_overreach


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_state_space_artifacts(
    snapshots: list[dict],
    transitions: list[dict],
    trajectories: list[dict],
    recommendations: list[dict],
    queries: list[dict],
) -> dict:
    for s in snapshots:
        reject_memory_overreach(s)
    validated_snapshots = []
    for s in snapshots:
        issues = validate_snapshot(s)
        validated_snapshots.append({"snapshot": s, "valid": not issues, "issues": issues})
    validated_transitions = []
    for t in transitions:
        issues = validate_transition(t)
        validated_transitions.append({"transition": t, "valid": not issues, "issues": issues})
    validated_trajectories = []
    for tr in trajectories:
        issues = validate_compressed_trajectory(tr)
        validated_trajectories.append({"trajectory": tr, "valid": not issues, "issues": issues})
    validated_recommendations = []
    for r in recommendations:
        issues = validate_repair_recommendation(r)
        validated_recommendations.append({"recommendation": r, "valid": not issues, "issues": issues})
    validated_queries = []
    for q in queries:
        issues = validate_query(q)
        validated_queries.append({"query": q, "valid": not issues, "issues": issues})
    result = {
        "snapshots": validated_snapshots,
        "transitions": validated_transitions,
        "trajectories": validated_trajectories,
        "recommendations": validated_recommendations,
        "queries": validated_queries,
        "snapshot_count": len(validated_snapshots),
        "transition_count": len(validated_transitions),
        "trajectory_count": len(validated_trajectories),
        "recommendation_count": len(validated_recommendations),
        "query_count": len(validated_queries),
        "all_snapshots_valid": all(v["valid"] for v in validated_snapshots),
        "all_transitions_valid": all(v["valid"] for v in validated_transitions),
        "all_trajectories_valid": all(v["valid"] for v in validated_trajectories),
        "all_recommendations_valid": all(v["valid"] for v in validated_recommendations),
        "all_queries_valid": all(v["valid"] for v in validated_queries),
        "hash_chain_valid": verify_hash_chain(transitions) if transitions else True,
        "compression_loss_declared": all(
            tr.get("compression_loss_declared") for tr in trajectories
        ) if trajectories else True,
        "all_recommendations_require_operator": all(
            r.get("operator_review_required") for r in recommendations
        ) if recommendations else True,
        "no_truth_elevation": all(
            not s.get("is_truth") for s in snapshots
        ),
        "no_authority_elevation": all(
            not s.get("is_authority") for s in snapshots
        ),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
