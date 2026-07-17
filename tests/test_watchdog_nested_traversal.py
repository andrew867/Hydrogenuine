"""Tests for watchdog nested proof directory traversal."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from agent_zero_soak_watchdog import (
    _find_nested_dirs, _find_backlog_topic_dirs,
    _aggregate_jsonl, _find_first_json, _gather_observation,
)


def _make_proof_tree(tmpdir):
    """Create a realistic nested proof directory tree."""
    root = os.path.join(tmpdir, "20260626T120000Z")
    sched = os.path.join(root, "20260626T120001Z")
    priority = os.path.join(sched, "20260626T120001Z")
    os.makedirs(priority)

    with open(os.path.join(sched, "scheduler_manifest.json"), "w") as f:
        json.dump({"verdict": "COMPLETED", "backlog_topics_started": 2, "backlog_topics_completed": 2}, f)

    with open(os.path.join(priority, "run_manifest.json"), "w") as f:
        json.dump({"verdict": "COMPLETED", "model_calls": 4, "promotions": 0,
                    "promotion_allowed": False}, f)

    with open(os.path.join(priority, "model_selection_receipts.jsonl"), "w") as f:
        for i in range(4):
            f.write(json.dumps({"selected_model_id": f"model_{i}", "call_intent": "summary"}) + "\n")

    with open(os.path.join(priority, "model_inference_receipts.jsonl"), "w") as f:
        for i in range(4):
            f.write(json.dumps({"model_id": f"model_{i}", "status": "success", "output_tokens": 50}) + "\n")

    with open(os.path.join(priority, "model_rotation_summary.json"), "w") as f:
        json.dump({"usage_counts": {"model_0": 1, "model_1": 1, "model_2": 1, "model_3": 1}}, f)

    with open(os.path.join(priority, "telemetry_summary.json"), "w") as f:
        json.dump({"model_calls_succeeded": 4, "model_calls_failed": 0, "model_calls_timed_out": 0,
                    "model_calls_skipped": 0}, f)

    cp_dir = os.path.join(priority, "checkpoints")
    os.makedirs(cp_dir)
    with open(os.path.join(cp_dir, "completed.json"), "w") as f:
        json.dump({"stage": "completed"}, f)

    # Backlog topics
    for tid in ["topic_a", "topic_b"]:
        td = os.path.join(sched, "backlog", "topics", tid)
        os.makedirs(td)
        with open(os.path.join(td, "topic_manifest.json"), "w") as f:
            json.dump({"topic_id": tid, "status": "complete"}, f)
        with open(os.path.join(td, "model_selection_receipts.jsonl"), "w") as f:
            f.write(json.dumps({"selected_model_id": f"model_{tid}"}) + "\n")
        with open(os.path.join(td, "model_inference_receipts.jsonl"), "w") as f:
            f.write(json.dumps({"model_id": f"model_{tid}", "status": "success"}) + "\n")

    return root


def test_find_nested_dirs_flat():
    with tempfile.TemporaryDirectory() as tmpdir:
        dirs = _find_nested_dirs(tmpdir)
        assert len(dirs) == 1
        assert dirs[0] == tmpdir


def test_find_nested_dirs_deep():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        dirs = _find_nested_dirs(root)
        assert len(dirs) >= 3  # root, sched, priority


def test_find_backlog_topic_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        topics = _find_backlog_topic_dirs(root)
        assert len(topics) == 2


def test_aggregate_receipts_from_nested():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        dirs = _find_nested_dirs(root)
        topics = _find_backlog_topic_dirs(root)
        all_dirs = dirs + topics
        count = _aggregate_jsonl(all_dirs, "model_selection_receipts.jsonl")
        assert count == 6  # 4 from priority + 1 each from 2 topics


def test_distinct_models_from_nested():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        dirs = _find_nested_dirs(root)
        rot = _find_first_json(dirs, "model_rotation_summary.json")
        assert len(rot.get("usage_counts", {})) == 4


def test_source_screenshots_from_nested():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        dirs = _find_nested_dirs(root)
        priority = dirs[-1]  # deepest
        with open(os.path.join(priority, "source_screenshot_receipts.jsonl"), "w") as f:
            f.write(json.dumps({"captured": True, "url": "http://example.com"}) + "\n")
            f.write(json.dumps({"captured": True, "url": "http://example.org"}) + "\n")
        count = _aggregate_jsonl(dirs, "source_screenshot_receipts.jsonl")
        assert count == 2


def test_warning_on_unknown_layout():
    with tempfile.TemporaryDirectory() as tmpdir:
        obs = _gather_observation(tmpdir, 1, 0)
        assert obs.get("artifact_discovery_warning") is not None


def test_watchdog_never_mutates():
    """Watchdog observation should not create any files in the proof dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        before = set()
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                before.add(os.path.join(dirpath, fn))
        _gather_observation(root, 1, 0)
        after = set()
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                after.add(os.path.join(dirpath, fn))
        assert before == after, f"Watchdog created files: {after - before}"


def test_gather_reports_nonzero():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = _make_proof_tree(tmpdir)
        obs = _gather_observation(root, 1, 0)
        assert obs["selection_receipts"] > 0
        assert obs["inference_receipts"] > 0
        assert obs["distinct_models_used"] > 0
        assert obs["run_status"] == "completed"
        assert obs["promotion_count"] == 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
