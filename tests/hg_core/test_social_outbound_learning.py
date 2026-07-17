from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from hg_core.live_social_gate import live_social_enabled
from hg_core.task_graph import native_task_tools as ntt
from hg_core.task_graph.social_outbound_learning import (
    audit_draft_artifact,
    audit_notification_entry,
    audit_recent_outbound,
    classify_outbound_content,
    load_active_lessons,
    outbound_learning_enabled,
    record_outbound_lesson,
    synthesize_lesson_prompt_block,
)


FIXTURES = Path("tests/fixtures/social_outbound")


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_classify_operator_leak():
    kind, severity, _ = classify_outbound_content(_fixture("operator_leak_moltbook.txt"), kind="reply", platform="moltbook")
    assert kind == "operator_leak"
    assert severity == "critical"


def test_classify_structured_decision_leak():
    kind, severity, _ = classify_outbound_content(_fixture("json_research_post.json"), kind="post", platform="moltbook")
    assert kind == "structured_decision_leak"
    assert severity == "critical"


def test_classify_template_bloat():
    kind, _, _ = classify_outbound_content(_fixture("reading_thread_reply.txt"), kind="reply", platform="fourclaw")
    assert kind == "template_bloat"


def test_classify_meta_navel_gaze():
    kind, _, _ = classify_outbound_content(_fixture("meta_navel_post.txt"), kind="post", platform="moltbook")
    assert kind == "meta_navel_gaze"


def test_classify_good_take():
    kind, severity, _ = classify_outbound_content(_fixture("good_banking_reply.txt"), kind="reply", platform="moltbook")
    assert kind == "good_take"
    assert severity == "positive"


def test_record_and_load_lessons(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "memory/automation/outbound_lessons").mkdir(parents=True)
    lesson_id = record_outbound_lesson(
        tmp_path,
        {
            "platform": "moltbook",
            "task_name": "moltbook-engage",
            "kind": "template_bloat",
            "severity": "high",
            "source": "test",
            "lesson_text": "no meta openers",
            "prompt_guardrail": "Do not open with reading the thread",
            "recurrence_key": "template_bloat:moltbook",
        },
        dedupe_hours=0,
    )
    assert lesson_id
    lessons = load_active_lessons(tmp_path, platform="moltbook", limit=8)
    assert len(lessons) == 1
    assert lessons[0]["lesson_id"] == lesson_id


def test_load_active_lessons_platform_filter(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "memory/automation/outbound_lessons").mkdir(parents=True)
    for platform in ("moltbook", "fourclaw"):
        for index in range(10):
            record_outbound_lesson(
                tmp_path,
                {
                    "platform": platform,
                    "task_name": f"{platform}-engage",
                    "kind": "template_bloat",
                    "severity": "high",
                    "source": "test",
                    "lesson_text": f"lesson {index}",
                    "prompt_guardrail": f"guard {index}",
                    "recurrence_key": f"template_bloat:{platform}:{index}",
                },
                dedupe_hours=0,
            )
    scoped = load_active_lessons(tmp_path, platform="moltbook", limit=8)
    assert len(scoped) == 8
    assert all(row.get("platform") == "moltbook" for row in scoped)


def test_synthesize_lesson_prompt_block_respects_limit():
    lessons = [
        {"severity": "critical", "prompt_guardrail": "A" * 200},
        {"severity": "high", "prompt_guardrail": "B" * 200},
        {"severity": "positive", "prompt_guardrail": "good example"},
    ]
    block = synthesize_lesson_prompt_block(lessons)
    assert len(block) <= 800
    assert "RECENT MISTAKES" in block
    assert "POSITIVE ANCHORS" in block


def test_escalate_recurring_lessons_emits_suggestion(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / "memory/automation/outbound_lessons"
    store.mkdir(parents=True)
    path = store / "global.jsonl"
    for index in range(3):
        row = {
            "lesson_id": f"les_test_{index}",
            "recorded_at": "2026-06-11T10:00:00Z",
            "platform": "moltbook",
            "task_name": "moltbook-engage",
            "kind": "template_bloat",
            "severity": "high",
            "source": "test",
            "lesson_text": f"repeat {index}",
            "prompt_guardrail": "repeat",
            "recurrence_key": "template_bloat:moltbook",
            "status": "active",
        }
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
    with patch("hg_core.learning.suggestions.publish_tuning_suggestion", return_value="tune_test") as publish:
        from hg_core.task_graph.social_outbound_learning import escalate_recurring_lessons

        suggestion_id = escalate_recurring_lessons(tmp_path)
    assert suggestion_id == "tune_test"
    publish.assert_called_once()


def test_audit_notification_entry_incident():
    line = (FIXTURES / "notification_incident_20260611.jsonl").read_text(encoding="utf-8").splitlines()[0]
    entry = json.loads(line)
    lesson = audit_notification_entry(entry)
    assert lesson is not None
    assert lesson["kind"] == "structured_decision_leak"


def test_audit_draft_artifact_publish_blocked(tmp_path: Path):
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(
        json.dumps(
            {
                "platform": "fourclaw",
                "task": "fourclaw-engage",
                "draft_text": _fixture("reading_thread_reply.txt"),
                "publish_blocked": True,
                "publish_blocked_reason": "template_bloat",
            }
        ),
        encoding="utf-8",
    )
    lesson = audit_draft_artifact(draft_path)
    assert lesson is not None
    assert lesson["kind"] == "template_bloat"


def test_duplicate_recurrence_key_dedupes(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "memory/automation/outbound_lessons").mkdir(parents=True)
    payload = {
        "platform": "moltbook",
        "task_name": "moltbook-engage",
        "kind": "operator_leak",
        "severity": "critical",
        "source": "test",
        "lesson_text": "x",
        "prompt_guardrail": "x",
        "recurrence_key": "operator_leak:moltbook",
    }
    first = record_outbound_lesson(tmp_path, payload)
    second = record_outbound_lesson(tmp_path, payload)
    assert first
    assert second is None


def test_learning_state_does_not_enable_live_posting(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_APIS", raising=False)
    (tmp_path / "memory/automation/outbound_lessons").mkdir(parents=True)
    record_outbound_lesson(
        tmp_path,
        {
            "platform": "moltbook",
            "task_name": "moltbook-engage",
            "kind": "good_take",
            "severity": "positive",
            "source": "test",
            "lesson_text": "great post",
            "prompt_guardrail": "match tone",
            "recurrence_key": "good_take:moltbook",
        },
        dedupe_hours=0,
    )
    assert load_active_lessons(tmp_path, platform="moltbook")
    assert live_social_enabled() is False


def test_blocked_outcome_no_external_calls(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / ".hg_root").write_text("", encoding="utf-8")
    monkeypatch.setattr(ntt, "get_workspace_root", lambda: tmp_path)
    monkeypatch.setenv("OUTBOUND_LEARNING_ENABLED", "1")
    result = ntt._outbound_validation_no_action(
        tmp_path,
        task_name="moltbook-engage",
        platform="moltbook",
        blocked_reason="structured_decision_leak:json_body",
        topic_hint="thread",
        draft_text='{"action": "research", "reason": "thin"}',
        kind="reply",
    )
    assert result["external_calls"] == 0
    assert result["outputs"]["result"]["status"] == "no_action"
    assert result["outputs"]["result"].get("lesson_recorded") is True


def test_audit_recent_outbound_reads_fixture_notifications(tmp_path: Path):
    notif_dir = tmp_path / "memory/automation/notifications"
    notif_dir.mkdir(parents=True)
    (notif_dir / "human_notifications.jsonl").write_text(
        (FIXTURES / "notification_incident_20260611.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    audit = audit_recent_outbound(tmp_path, since_hours=72)
    assert audit["lessons_found"] >= 1
    assert audit["candidates"]


@pytest.mark.parametrize("enabled", ["1", "0"])
def test_outbound_learning_flag(enabled, monkeypatch):
    monkeypatch.setenv("OUTBOUND_LEARNING_ENABLED", enabled)
    assert outbound_learning_enabled() == (enabled == "1")
