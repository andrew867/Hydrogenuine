"""F02 state-space memory organ fixture data."""

from __future__ import annotations

import hashlib
import json


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def fixture_state_snapshot(seq: int = 1, mode: str = "fixture_only") -> dict:
    snap = {
        "snapshot_id": f"snap-{seq:03d}",
        "sequence": seq,
        "timestamp": f"2026-06-22T10:{seq:02d}:00Z",
        "subsystems": {
            "inference": "idle",
            "soak": "paused",
            "ledger": "clean",
        },
        "active_goals": [],
        "current_mode": mode,
        "checkpoint_ref": None,
        "proof_refs": [],
        "uncertainty_score": 0.1,
        "is_truth": False,
        "is_authority": False,
    }
    snap["state_hash"] = _hash(snap)
    return snap


def fixture_state_transition(from_seq: int = 1, to_seq: int = 2) -> dict:
    prev = fixture_state_snapshot(from_seq)
    nxt = fixture_state_snapshot(to_seq)
    return {
        "transition_id": f"trans-{from_seq:03d}-{to_seq:03d}",
        "previous_state_hash": prev["state_hash"],
        "next_state_hash": nxt["state_hash"],
        "transition_reason": "scheduled_observation",
        "observed_events": ["soak_tick", "ledger_write"],
        "degradation_marker": False,
        "improvement_marker": False,
        "uncertainty_delta": 0.0,
    }


def fixture_stable_run_snapshots() -> list[dict]:
    return [fixture_state_snapshot(i) for i in range(1, 4)]


def fixture_degrading_run_snapshots() -> list[dict]:
    snaps = []
    for i in range(1, 4):
        s = fixture_state_snapshot(i)
        s["uncertainty_score"] = 0.1 * i + 0.2
        s["subsystems"]["soak"] = "warning" if i >= 2 else "paused"
        s["state_hash"] = _hash(s)
        snaps.append(s)
    return snaps


def fixture_stale_snapshot() -> dict:
    s = fixture_state_snapshot(1)
    s["timestamp"] = "2026-06-01T00:00:00Z"
    s["state_hash"] = _hash(s)
    return s


def fixture_contradictory_snapshots() -> tuple[dict, dict]:
    a = fixture_state_snapshot(5)
    a["subsystems"]["inference"] = "active"
    a["state_hash"] = _hash(a)
    b = fixture_state_snapshot(5)
    b["subsystems"]["inference"] = "idle"
    b["state_hash"] = _hash(b)
    return a, b


def fixture_compressed_trajectory() -> dict:
    return {
        "trajectory_id": "traj-001",
        "window_start": "2026-06-22T10:01:00Z",
        "window_end": "2026-06-22T10:03:00Z",
        "snapshot_count": 3,
        "summary": "Stable operation across 3 observations. No degradation.",
        "compression_loss_declared": True,
        "dropped_detail": ["per-subsystem latency", "individual event timestamps"],
        "stale_markers": [],
        "decay_metadata": {"decay_rate": 0.0, "staleness_threshold_hours": 24},
        "repeated_failures": [],
        "repeated_successes": ["ledger_write"],
    }


def fixture_lossy_compression() -> dict:
    t = fixture_compressed_trajectory()
    t["trajectory_id"] = "traj-002"
    t["compression_loss_declared"] = True
    t["dropped_detail"] = ["full subsystem state vectors", "raw event payloads", "timing jitter"]
    return t


def fixture_repair_recommendation() -> dict:
    return {
        "recommendation_id": "rec-001",
        "source_observations": ["snap-002", "snap-003"],
        "affected_subsystem": "soak",
        "recommended_action": "Inspect soak module for rising uncertainty",
        "evidence_links": ["trans-001-002", "trans-002-003"],
        "confidence": 0.6,
        "uncertainty": 0.4,
        "risk": "medium",
        "operator_review_required": True,
        "is_permission": False,
        "is_patch_approval": False,
        "authorizes_tools": False,
    }


def fixture_tool_auth_recommendation() -> dict:
    return {
        "recommendation_authorizes_tools": True,
        "recommendation_is_patch_approval": True,
        "recommendation_is_permission": True,
    }


def fixture_patch_application_attempt() -> dict:
    return {
        "memory_applies_patch": True,
        "recommendation_is_patch_approval": True,
    }


def fixture_phase19_laundering_attempt() -> dict:
    return {"memory_marks_phase19_green": True}


def fixture_phase24_laundering_attempt() -> dict:
    return {"memory_marks_phase24_full_overnight_green": True}


def fixture_secret_material_snapshot() -> dict:
    s = fixture_state_snapshot(99)
    s["subsystems"]["api_key"] = "sk-live-abc123secret"
    s["state_hash"] = _hash(s)
    return s


def fixture_state_query() -> dict:
    return {
        "query_id": "q-001",
        "query_type": "snapshot_range",
        "from_sequence": 1,
        "to_sequence": 3,
        "max_results": 10,
        "is_truth": False,
        "is_authority": False,
        "authorizes_actions": False,
    }


def fixture_memory_status_snapshot() -> dict:
    return {
        "snapshots_count": 3,
        "transitions_count": 2,
        "trajectories_count": 1,
        "recommendations_count": 1,
        "stale_snapshots": 0,
        "contradictions": 0,
        "phase19_yellow": True,
        "phase24_infrastructure_only": True,
    }
