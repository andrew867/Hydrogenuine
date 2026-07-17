"""Negative control — old template bot must not pass as autonomous."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from scripts.dev.verify_overnight_cognitive_run import verify_overnight_cognitive_run

OLD_RUN = WORKSPACE / ".hg-local/soak/runs/overnight-draft-20260617T051229Z"

FIXTURE_COMMENT = (
    "[DRAFT COMMENT — NOT POSTED] Thoughtful question about bounded soak receipts. "
    "Context: bounded overnight review."
)
FIXTURE_REPLY = "Draft reply to message mcmsg-fixture-001: acknowledge receipt and note that live send is off."


def _write_template_bot_run(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    drafts = []
    bodies = [
        "Late-night note: resilient systems earn trust through bounded behavior.",
        FIXTURE_COMMENT,
        FIXTURE_REPLY,
    ]
    for i in range(12):
        body = bodies[i % len(bodies)]
        drafts.append({
            "draft_id": f"odraft-{i:04d}",
            "draft_type": ["post", "comment", "reply"][i % 3],
            "draft_text": body,
            "draft_text_hash": f"hash-{i % 3}",
            "risk_class": "low",
            "status": "queued_for_morning_review",
            "reason_for_draft": "Overnight comment draft from local thread context",
            "publish_attempted": False,
            "sent": False,
        })
    (run_dir / "draft_queue.jsonl").write_text(
        "\n".join(json.dumps(d) for d in drafts) + "\n",
        encoding="utf-8",
    )
    (run_dir / "event_log.jsonl").write_text(
        json.dumps({"event": "SOAK_START", "advisory_only": True}) + "\n",
        encoding="utf-8",
    )


def test_old_template_bot_negative_control_fails(tmp_path: Path):
    run_dir = tmp_path / "template_bot"
    _write_template_bot_run(run_dir)
    report = verify_overnight_cognitive_run(run_dir)
    assert report["verdict"] == "RED_TEMPLATE_BOT_NOT_AUTONOMOUS"
    assert "RED_FIXTURE_CORPUS_IN_DRAFTS" in report["failures"]


def test_fixture_rehearsal_not_autonomous(tmp_path: Path):
    run_dir = tmp_path / "plumbing"
    run_dir.mkdir()
    draft = {
        "draft_id": "odraft-plumb",
        "draft_type": "post",
        "draft_text": "A unique operator-authored note about supervisor plumbing only.",
        "draft_text_hash": "unique-hash-1",
        "risk_class": "low",
        "status": "queued_for_morning_review",
        "publish_attempted": False,
        "sent": False,
    }
    (run_dir / "draft_queue.jsonl").write_text(json.dumps(draft) + "\n", encoding="utf-8")
    report = verify_overnight_cognitive_run(run_dir)
    assert report["verdict"] == "YELLOW_FIXTURE_REHEARSAL_NOT_COGNITIVE"
    assert not report["autonomous_artifacts"]


@pytest.mark.skipif(not OLD_RUN.is_dir(), reason="old run artifacts not present locally")
def test_real_old_run_classified_template_bot():
    report = verify_overnight_cognitive_run(OLD_RUN)
    assert report["verdict"] == "RED_TEMPLATE_BOT_NOT_AUTONOMOUS"


def test_no_publish_side_effect_required_for_phase_1(tmp_path: Path):
    run_dir = tmp_path / "safe"
    _write_template_bot_run(run_dir)
    report = verify_overnight_cognitive_run(run_dir)
    assert "RED_LIVE_SIDE_EFFECT_DETECTED" not in report["failures"]
    drafts = [
        json.loads(line)
        for line in (run_dir / "draft_queue.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(not d.get("publish_attempted") for d in drafts)
    assert all(not d.get("sent") for d in drafts)
