"""
Control Surface Pack 8: Operator cockpit — orchestration, fusion cards, autonomy presets.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.control_surface import (
    orchestration_preflight,
    orchestration_apply,
    get_cards_feed,
    get_card_detail,
    list_autonomy_presets,
    preview_preset_delta,
    apply_autonomy_preset,
)


def test_orchestration_preflight_allowed_when_low_drift(tmp_path: Path) -> None:
    """Preflight allows when no drift safeguards and low scores."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text(
        '{"score":0.2,"drift_id":"d1"}\n',
        encoding="utf-8",
    )
    (root / "drift_alerts.jsonl").write_text("", encoding="utf-8")
    out = orchestration_preflight(tmp_path, drift_score_threshold=0.7)
    assert out["allowed"] is True
    assert "drift" in out["checks"]


def test_orchestration_preflight_blocked_when_high_drift(tmp_path: Path) -> None:
    """Preflight blocked when drift score above threshold."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text(
        '{"score":0.9,"drift_id":"d1"}\n',
        encoding="utf-8",
    )
    (root / "drift_alerts.jsonl").write_text("", encoding="utf-8")
    out = orchestration_preflight(tmp_path, drift_score_threshold=0.7)
    assert out["allowed"] is False
    assert "drift_score" in out["reason"] or "threshold" in out["reason"] or out["reason"]


def test_orchestration_apply_emits(tmp_path: Path) -> None:
    """orchestration_apply emits ORCHESTRATION_ACTION_APPLIED."""
    scope = {"type": "run", "id": "test"}
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    eid = orchestration_apply(
        action_type="scale_up",
        target_ref={"type": "group", "id": "g1"},
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert eid
    from hg_core.ledger.ledger_writer import iterate_events
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "ORCHESTRATION_ACTION_APPLIED" for ev in events)


def test_cards_feed_returns_list(tmp_path: Path) -> None:
    """Cards feed returns list (possibly empty)."""
    feed = get_cards_feed(tmp_path, limit=10)
    assert isinstance(feed, list)


def test_card_detail_drift(tmp_path: Path) -> None:
    """Card detail returns drift card when present."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text(
        '{"drift_id":"d99","score":0.5,"ts":"2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    card = get_card_detail(tmp_path, "drift_d99")
    assert card is not None
    assert card.get("type") == "drift"
    assert card.get("score") == 0.5


def test_card_detail_unknown_returns_none(tmp_path: Path) -> None:
    """Card detail returns None for unknown card_id."""
    assert get_card_detail(tmp_path, "unknown_xyz") is None


def test_list_autonomy_presets_empty_without_artifacts(tmp_path: Path) -> None:
    """List presets returns empty when no artifacts."""
    presets = list_autonomy_presets(tmp_path)
    assert presets == []


def test_list_and_preview_and_apply_preset(tmp_path: Path) -> None:
    """List presets, preview delta, apply preset with expiry."""
    root = tmp_path / "artifacts" / "autonomy_presets"
    root.mkdir(parents=True, exist_ok=True)
    (root / "conservative.json").write_text(
        '{"preset_id":"conservative","name":"Conservative","autonomy_level":"low","constraints":["no_external"]}\n',
        encoding="utf-8",
    )
    presets = list_autonomy_presets(tmp_path)
    assert len(presets) == 1
    assert presets[0].get("preset_id") == "conservative"
    assert presets[0].get("autonomy_level") == "low"

    delta = preview_preset_delta(tmp_path, "conservative", target_ref={"type": "entity", "id": "e1"})
    assert "preset" in delta
    assert delta.get("preset") is not None
    assert delta["preset"].get("autonomy_level") == "low"
    assert "delta" in delta

    scope = {"type": "run", "id": "test"}
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    eid = apply_autonomy_preset(
        preset_id="conservative",
        target_ref={"type": "entity", "id": "e1"},
        scope=scope,
        actor=actor,
        expiry_hours=24,
        workspace_root=tmp_path,
    )
    assert eid
    from hg_core.ledger.ledger_writer import iterate_events
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "AUTONOMY_PRESET_APPLIED" for ev in events)


def test_preview_preset_not_found(tmp_path: Path) -> None:
    """Preview preset returns error when preset not found."""
    delta = preview_preset_delta(tmp_path, "nonexistent")
    assert delta.get("error") == "preset_not_found"


def test_apply_preset_not_found_raises(tmp_path: Path) -> None:
    """Apply preset raises FileNotFoundError when preset missing."""
    scope = {"type": "run", "id": "test"}
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    with pytest.raises(FileNotFoundError):
        apply_autonomy_preset(
            preset_id="nonexistent",
            target_ref={"type": "entity", "id": "e1"},
            scope=scope,
            actor=actor,
            workspace_root=tmp_path,
        )
