"""Shared fixtures for hg_learning tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def swarm_proof_bundle(tmp_path: Path) -> Path:
    """Minimal PROOF_SCHEMA bundle with swarm artifacts."""
    bundle = tmp_path / "swarm_bundle"
    bundle.mkdir()
    summary = {
        "label": "test_swarm",
        "started_at": "2026-06-10T00:00:00Z",
        "ended_at": "2026-06-10T00:00:01Z",
        "checks_passed": True,
        "swarm_run_id": "swarm-test-1",
        "syndrome_count": 1,
        "correction_count": 1,
    }
    (bundle / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (bundle / "checks.json").write_text(json.dumps([{"name": "ok", "pass": True}]), encoding="utf-8")
    (bundle / "ENVIRONMENT.json").write_text(json.dumps({"git_commit_hash": "abc"}), encoding="utf-8")
    (bundle / "VERSIONS.txt").write_text("test=1\n", encoding="utf-8")
    artifacts = {
        "verification_graph": {"graph_id": "vg1", "node_ids": ["a", "b"], "edge_pairs": [["a", "b"]]},
        "syndrome_count": 1,
        "syndromes": [
            {
                "report_id": "syn1",
                "syndrome_locations": ["child_0", "child_1"],
                "confidence": 0.9,
            }
        ],
        "correction_actions": [
            {
                "action_id": "ca1",
                "report_id": "syn1",
                "target_entity": "child_0",
                "correction_weight": 0.85,
                "approved": False,
                "rationale": "test",
            }
        ],
    }
    (bundle / "artifacts.json").write_text(json.dumps(artifacts), encoding="utf-8")
    return bundle


@pytest.fixture
def behavioral_proof_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "behavioral_bundle"
    bundle.mkdir()
    summary = {
        "label": "test_pick_place",
        "started_at": "2026-06-10T01:00:00Z",
        "ended_at": "2026-06-10T01:00:01Z",
        "checks_passed": True,
        "behavioral_metrics": {
            "task_completion": 1.0,
            "safety_violations": 0.0,
            "path_efficiency": 0.85,
        },
    }
    (bundle / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (bundle / "checks.json").write_text(json.dumps([{"name": "ok", "pass": True}]), encoding="utf-8")
    (bundle / "ENVIRONMENT.json").write_text(
        json.dumps({"feature_flags": {"camera": "enabled"}}),
        encoding="utf-8",
    )
    (bundle / "VERSIONS.txt").write_text("test=1\n", encoding="utf-8")
    return bundle
