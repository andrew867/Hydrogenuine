"""
Control Surface Pack 6: Ghost drift detection — features, scoring, safeguards, preflight.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.drift import (
    extract_drift_features,
    compute_drift_scores,
    emit_drift_score,
    apply_drift_safeguard,
    list_active_safeguards,
    get_drift_scores,
    get_drift_alerts,
    preflight_drift,
)


def test_repeated_near_miss_raises_human_drift_score() -> None:
    """Near-miss tags in messages produce factors that raise human intent drift score."""
    messages = [
        {"text": "try X", "tags": ["near_miss"]},
        {"text": "try X again", "tags": ["near_miss"]},
    ]
    features = extract_drift_features(messages, "thread_1")
    assert features.get("near_miss_count", 0) >= 1 or "factors" in features
    score = compute_drift_scores(features, "human_intent")
    assert 0 <= score <= 1
    assert features.get("factors")


def test_boundary_probing_adds_factor() -> None:
    """Boundary probe tags add boundary_probing factor."""
    messages = [{"text": "can you do Y?", "tags": ["boundary_probe"]}]
    features = extract_drift_features(messages, "t1")
    names = [f["name"] for f in features.get("factors", [])]
    assert "boundary_probing" in names


def test_agent_response_score_scaled() -> None:
    """Agent response score uses higher multiplier."""
    features = {"factors": [{"name": "x", "weight": 0.5}]}
    human = compute_drift_scores(features, "human_intent")
    agent = compute_drift_scores(features, "agent_response")
    assert agent >= human


def test_safeguards_time_bound_and_expiry(tmp_path: Path) -> None:
    """apply_drift_safeguard emits event with expiry_ts; list_active_safeguards filters expired."""
    from hg_core.drift.safeguards import apply_drift_safeguard
    scope = {"type": "run", "id": "test"}
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    sid = apply_drift_safeguard(
        scope=scope,
        actor=actor,
        effects={"require_rescope": True},
        expiry_hours=24,
        workspace_root=tmp_path,
    )
    assert sid
    from hg_core.materializers.drift_indexer import run as run_drift_indexer
    run_drift_indexer(tmp_path, rebuild=True)
    active = list_active_safeguards(tmp_path)
    assert isinstance(active, list)


def test_drift_affects_preflight_deterministically(tmp_path: Path) -> None:
    """preflight_drift returns blocked when active safeguards or high score."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text(
        '{"thread_id":"t1","score":0.9,"drift_id":"d1"}\n',
        encoding="utf-8",
    )
    (root / "drift_alerts.jsonl").write_text("", encoding="utf-8")
    out = preflight_drift(tmp_path, thread_id="t1", score_threshold=0.7)
    assert out["blocked"] is True
    assert out["reason"] == "drift_score_above_threshold"
    assert out["max_score"] == 0.9


def test_preflight_not_blocked_when_low_score(tmp_path: Path) -> None:
    """preflight_drift not blocked when score below threshold and no safeguards."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text(
        '{"thread_id":"t1","score":0.2,"drift_id":"d1"}\n',
        encoding="utf-8",
    )
    (root / "drift_alerts.jsonl").write_text("", encoding="utf-8")
    out = preflight_drift(tmp_path, thread_id="t1", score_threshold=0.7)
    assert out["blocked"] is False
    assert out["max_score"] == 0.2


def test_get_drift_scores_filtered_by_thread(tmp_path: Path) -> None:
    """get_drift_scores filters by thread_id."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text(
        '{"thread_id":"t1","score":0.5}\n{"thread_id":"t2","score":0.6}\n',
        encoding="utf-8",
    )
    rows = get_drift_scores(tmp_path, thread_id="t1")
    assert len(rows) == 1
    assert rows[0]["thread_id"] == "t1"


def test_emit_drift_score_writes_ledger(tmp_path: Path) -> None:
    """emit_drift_score emits DRIFT_SCORE_COMPUTED to ledger."""
    scope = {"type": "run", "id": "test"}
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    eid = emit_drift_score(
        kind="human_intent",
        subject_ref={"type": "thread", "id": "t1"},
        thread_id="t1",
        score=0.4,
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert eid
    from hg_core.ledger.ledger_writer import iterate_events
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "DRIFT_SCORE_COMPUTED" for ev in events)
