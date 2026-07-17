"""Operator-confirmed publish after observation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.bounded_soak.operator_publish import (
    observation_checkpoint_ready,
    operator_confirmed,
    write_operator_confirmation,
)


def test_auto_publish_without_confirm_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "operator_intent.json").write_text(
        json.dumps({"observation_minutes": 0}), encoding="utf-8"
    )
    (run_dir / "command_log.jsonl").write_text(
        '{"event":"SOAK_START","ts":"2020-01-01T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    ready, verdict = observation_checkpoint_ready(run_dir)
    assert ready
    assert "OPERATOR_CONFIRMATION" in verdict or verdict.startswith("GREEN_OBSERVATION")


def test_confirm_writes_receipt(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "operator_intent.json").write_text(
        json.dumps({"observation_minutes": 0}), encoding="utf-8"
    )
    (run_dir / "command_log.jsonl").write_text(
        '{"event":"SOAK_START","ts":"2020-01-01T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    receipt = write_operator_confirmation(run_dir, max_posts=2, min_seconds_between_posts=100)
    assert receipt["confirmed"] is True
    assert operator_confirmed(run_dir)
    assert (run_dir / "operator_publish_confirmation.json").is_file()


def test_confirm_blocked_after_stop(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr(
        "hg_runtime.bounded_soak.operator_publish.stop_or_panic_active",
        lambda workspace=None: True,
    )
    (run_dir / "operator_intent.json").write_text(json.dumps({"observation_minutes": 0}), encoding="utf-8")
    (run_dir / "command_log.jsonl").write_text(
        '{"event":"SOAK_START","ts":"2020-01-01T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="stop or panic"):
        write_operator_confirmation(run_dir, max_posts=1, min_seconds_between_posts=60)
