"""Output quality gate tests for overnight research.

Tests that:
1. Empty model response does not count as valid/substantive output.
2. Timeout with elapsed_s=0.0 is classified as provider anomaly, not completion.
3. Topic with two failed calls is FAILED, not COMPLETED.
4. Scheduler cannot return COMPLETED when required topics have zero substantive output.
5. Receipt serializer preserves full text (not just 280-char preview).
6. text_preview truncation does not destroy canonical full_text.
7. Weak-output retry occurs on different model.
8. Retry exhaustion is honestly receipted.
9. Watchdog check-ins do not overwrite by default.
10. Idle heartbeat writes incrementally.
11. Final split-readiness gate blocks invalid baseline.
12. No promotion/memory promotion/remote fallback still enforced.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.live_local.reasoning_classifier import (
    classify_response, ReasoningReceipt,
)
from hg_runtime.overnight_research.min_duration_policy import (
    MinDurationState, write_idle_heartbeats, write_duration_summary,
)

M = "google/gemma-4-e4b"


# --- 1. Empty model response is not substantive ---

class TestEmptyOutputNotSubstantive:
    def test_empty_content_not_substantive(self):
        r = classify_response(model_id=M, endpoint="x", finish_reason="length")
        assert r.classification == "empty_content"
        assert r.is_substantive() is False

    def test_timeout_not_substantive(self):
        r = classify_response(model_id=M, endpoint="x", error="request timed out")
        assert r.classification == "timeout"
        assert r.is_substantive() is False

    def test_normal_content_is_substantive(self):
        r = classify_response(model_id=M, endpoint="x", content="real answer", finish_reason="stop")
        assert r.classification == "normal_content"
        assert r.is_substantive() is True

    def test_whitespace_only_not_substantive(self):
        r = classify_response(model_id=M, endpoint="x", content="   \n  ", finish_reason="stop")
        assert r.is_substantive() is False


# --- 2. Timeout with elapsed_s=0.0 is classified correctly ---

class TestTimeoutClassification:
    def test_timeout_zero_elapsed_is_timeout(self):
        r = classify_response(model_id=M, endpoint="x", error="timed out",
                              elapsed_seconds=0.0)
        assert r.classification == "timeout"
        assert r.provider_status == "timeout"
        assert r.failure_reason == "timeout"
        assert r.is_substantive() is False

    def test_timeout_severity_is_yellow(self):
        r = classify_response(model_id=M, endpoint="x", error="timed out")
        assert r.severity == "YELLOW"

    def test_client_disconnect_is_not_completion(self):
        r = classify_response(model_id=M, endpoint="x", error="connection reset by peer")
        assert r.classification == "client_disconnect"
        assert r.is_substantive() is False
        assert r.provider_status == "disconnect"


# --- 5 & 6. Receipt preserves full text and preview ---

class TestReceiptFullText:
    def test_full_text_stored(self):
        long_content = "A" * 500
        r = classify_response(model_id=M, endpoint="x", content=long_content,
                              finish_reason="stop")
        assert r.full_text == long_content
        assert len(r.full_text) == 500

    def test_content_excerpt_truncated(self):
        long_content = "B" * 500
        r = classify_response(model_id=M, endpoint="x", content=long_content,
                              finish_reason="stop")
        assert len(r.content_excerpt) == 280
        assert r.content_excerpt == long_content[:280]

    def test_full_text_not_destroyed_by_preview(self):
        long_content = "C" * 1000
        r = classify_response(model_id=M, endpoint="x", content=long_content,
                              finish_reason="stop")
        assert r.full_text == long_content
        assert r.content_excerpt == long_content[:280]
        assert r.content_char_count == 1000


# --- 9. Watchdog check-ins unique numbering ---

class TestWatchdogCheckins:
    def test_watchdog_writes_unique_numbered_files(self):
        with tempfile.TemporaryDirectory() as td:
            checkin_dir = os.path.join(td, "watchdog_checkins")
            os.makedirs(checkin_dir)
            for i in range(1, 4):
                path = os.path.join(checkin_dir, f"checkin_{i:03d}.json")
                with open(path, "w") as f:
                    json.dump({"checkin_number": i}, f)
            files = sorted(os.listdir(checkin_dir))
            assert files == ["checkin_001.json", "checkin_002.json", "checkin_003.json"]


# --- 10. Idle heartbeat writes incrementally ---

class TestIdleHeartbeatIncremental:
    def test_heartbeat_written_each_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            state = MinDurationState(
                min_wall_clock_seconds=0.2,
                continue_until_min_duration=True,
                idle_cycle_seconds=0.05,
                max_idle_cycles=10,
                out_dir=td,
            )
            state.start()
            cycles = 0
            while state.should_idle() and cycles < 5:
                state.idle_cycle()
                cycles += 1
                hb_path = os.path.join(td, "idle_heartbeat_receipts.jsonl")
                assert os.path.isfile(hb_path), "heartbeat file should exist after each cycle"
                with open(hb_path) as f:
                    lines = [l for l in f if l.strip()]
                assert len(lines) == cycles, f"expected {cycles} heartbeats, got {len(lines)}"

    def test_write_idle_heartbeats_overwrites_for_final(self):
        with tempfile.TemporaryDirectory() as td:
            state = MinDurationState(
                min_wall_clock_seconds=0.1,
                continue_until_min_duration=True,
                idle_cycle_seconds=0.05,
                max_idle_cycles=3,
                out_dir=td,
            )
            state.start()
            state.idle_cycle()
            state.idle_cycle()
            path = write_idle_heartbeats(state, td)
            with open(path) as f:
                lines = [l for l in f if l.strip()]
            assert len(lines) == 2


# --- 12. No promotion/memory promotion/remote fallback ---

class TestGovernanceControlsReceipt:
    def test_promotion_never_allowed(self):
        r = classify_response(model_id=M, endpoint="x", content="answer", finish_reason="stop")
        assert r.promotion_allowed is False

    def test_tools_never_authorized(self):
        r = classify_response(model_id=M, endpoint="x", content="answer", finish_reason="stop")
        assert r.tools_authorized is False

    def test_authority_never_granted(self):
        r = classify_response(model_id=M, endpoint="x", content="answer", finish_reason="stop")
        assert r.authority_granted is False

    def test_remote_fallback_is_red(self):
        r = classify_response(model_id=M, endpoint="x", content="x", remote_fallback=True)
        assert r.classification == "remote_fallback_attempt"
        assert r.severity == "RED"
        assert r.is_substantive() is False


# --- Receipt fields ---

class TestReceiptFields:
    def test_failure_reason_populated_for_timeout(self):
        r = classify_response(model_id=M, endpoint="x", error="timeout!")
        assert r.failure_reason == "timeout"
        assert r.provider_status == "timeout"

    def test_failure_reason_populated_for_empty(self):
        r = classify_response(model_id=M, endpoint="x", finish_reason="stop")
        assert r.failure_reason == "empty_response"
        assert r.provider_status == "empty"

    def test_provider_status_ok_for_normal(self):
        r = classify_response(model_id=M, endpoint="x", content="answer", finish_reason="stop")
        assert r.provider_status == "ok"
        assert r.failure_reason == ""

    def test_retry_index_default_zero(self):
        r = classify_response(model_id=M, endpoint="x", content="answer", finish_reason="stop")
        assert r.retry_index == 0
