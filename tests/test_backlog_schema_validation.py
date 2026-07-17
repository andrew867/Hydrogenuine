"""Tests for backlog schema validation and preflight doctor."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from hg_runtime.overnight_research.backlog_contract import (
    BacklogTopic, load_backlog_file,
)
from agent_zero_validate_backlog import validate_backlog


def _write_jsonl(tmpdir, lines):
    path = os.path.join(tmpdir, "backlog.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_valid_topic_accepted():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [{
            "topic_id": "test_1",
            "title": "Test topic",
            "question": "What is this test about?",
            "risk_mode": "normal",
        }])
        result = validate_backlog(path)
        assert result["status"] == "GREEN"
        assert result["topics_valid"] == 1
        assert result["topics_invalid"] == 0


def test_missing_topic_id_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [{
            "title": "No ID",
            "question": "What?",
        }])
        result = validate_backlog(path)
        assert result["topics_valid"] == 0
        assert result["topics_invalid"] == 1
        errors = result["invalid_details"][0]["errors"]
        assert any("topic_id" in e for e in errors)


def test_missing_question_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [{
            "topic_id": "no_q",
            "title": "No question",
        }])
        result = validate_backlog(path)
        assert result["topics_valid"] == 0
        assert any("question" in e for e in result["invalid_details"][0]["errors"])


def test_missing_title_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [{
            "topic_id": "no_title",
            "question": "What?",
        }])
        result = validate_backlog(path)
        assert result["topics_valid"] == 0
        assert any("title" in e for e in result["invalid_details"][0]["errors"])


def test_invalid_topics_write_receipts():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [
            {"topic_id": "bad1"},
            {"topic_id": "bad2", "title": "x"},
        ])
        result = validate_backlog(path, write_report=True, report_dir=tmpdir)
        assert os.path.isfile(os.path.join(tmpdir, "invalid_backlog_topics.jsonl"))
        assert os.path.isfile(os.path.join(tmpdir, "backlog_schema_report.json"))
        assert os.path.isfile(os.path.join(tmpdir, "backlog_schema_report.md"))


def test_all_invalid_blocks_green():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [
            {"topic": "wrong format"},
            {"topic": "also wrong"},
        ])
        result = validate_backlog(path)
        assert result["status"] == "RED"
        assert result["topics_valid"] == 0


def test_mixed_valid_invalid():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [
            {"topic_id": "good", "title": "Good", "question": "What?"},
            {"topic": "bad format"},
        ])
        result = validate_backlog(path)
        assert result["status"] == "YELLOW"
        assert result["topics_valid"] == 1
        assert result["topics_invalid"] == 1


def test_corrected_schema_passes():
    """The corrected backlog from HG-DEEP-SOAK-WATCHDOG-INPUT should validate."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "docs", "proofs", "autonomous_agent_zero",
        "HG-DEEP-SOAK-WATCHDOG-INPUT", "deep_soak_backlog.jsonl"
    )
    if not os.path.isfile(path):
        return  # skip if not available
    result = validate_backlog(path)
    assert result["topics_valid"] > 0, f"Corrected backlog should have valid topics, got {result}"


def test_load_backlog_file_validates():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_jsonl(tmpdir, [
            {"topic_id": "ok", "title": "OK", "question": "What?"},
            {"topic_id": "", "title": "Bad", "question": "No ID"},
        ])
        topics, skips = load_backlog_file(path)
        assert len(topics) == 1
        assert len(skips) == 1
        assert topics[0].topic_id == "ok"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
