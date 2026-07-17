"""Legacy auto-flip denial tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.social_capability.review_queue import enable_live_publish_auto_approve


def test_auto_approve_disabled(tmp_path: Path):
    result = enable_live_publish_auto_approve(tmp_path / "run")
    assert result["ok"] is False
    assert "RED_AUTO_PUBLISH_FLIP" in result["error"] or "DISABLED" in result.get("verdict", "")


def test_no_auto_publish_flip_in_overnight_orchestrator():
    from pathlib import Path

    text = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "agent_zero_overnight_soak.py"
    if text.is_file():
        src = text.read_text(encoding="utf-8")
        assert "AUTO_PUBLISH_FLIP" not in src or "OBSERVATION_CHECKPOINT_READY" in src
