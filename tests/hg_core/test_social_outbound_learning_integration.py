from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from hg_core.task_graph import native_task_tools as ntt
from hg_core.task_graph.social_outbound_learning import record_outbound_lesson

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = WORKSPACE_ROOT / "tests" / "fixtures" / "social_outbound"


def _use_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / ".hg_root").write_text("", encoding="utf-8")
    monkeypatch.setattr(ntt, "get_workspace_root", lambda: tmp_path)


def test_lifecycle_load_outbound_lessons_tool(tmp_path: Path, monkeypatch):
    _use_workspace(tmp_path, monkeypatch)
    (tmp_path / "memory/automation/outbound_lessons").mkdir(parents=True)
    record_outbound_lesson(
        tmp_path,
        {
            "platform": "moltbook",
            "task_name": "moltbook-engage",
            "kind": "operator_leak",
            "severity": "critical",
            "source": "test",
            "lesson_text": "no leaks",
            "prompt_guardrail": "Never echo operator goals",
            "recurrence_key": "operator_leak:moltbook",
        },
        dedupe_hours=0,
    )
    result = ntt.run_task_tool(
        "lifecycle.load_outbound_lessons",
        {"platform": "moltbook", "limit": 4},
    )
    assert result is not None and result["ok"] is True
    assert result["outputs"]["guardrail_block"]
    assert result["outputs"]["lessons_active"] is True


def test_generate_engage_reply_includes_guardrail(tmp_path: Path, monkeypatch):
    _use_workspace(tmp_path, monkeypatch)
    (tmp_path / "memory/automation/outbound_lessons").mkdir(parents=True)
    record_outbound_lesson(
        tmp_path,
        {
            "platform": "fourclaw",
            "task_name": "fourclaw-engage",
            "kind": "template_bloat",
            "severity": "high",
            "source": "test",
            "lesson_text": "no meta",
            "prompt_guardrail": "UNIQUE_GUARDRAIL_TOKEN_XYZ",
            "recurrence_key": "template_bloat:fourclaw",
        },
        dedupe_hours=0,
    )
    with patch.object(ntt, "_llm_complete", return_value="Direct take on the queue depth issue."):
        lifecycle = ntt._build_lifecycle_context(task_name="fourclaw-engage", platform="fourclaw")
    assert "UNIQUE_GUARDRAIL_TOKEN_XYZ" in lifecycle.get("guardrail_block", "")


def test_audit_and_record_tools(tmp_path: Path, monkeypatch):
    _use_workspace(tmp_path, monkeypatch)
    notif_dir = tmp_path / "memory/automation/notifications"
    notif_dir.mkdir(parents=True)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "timestamp": now,
        "task_name": "moltbook-auto-post",
        "summary": {
            "platform": "moltbook",
            "external_calls": 1,
            "body_snippet": '{"action": "research", "reason": "thread too thin"}',
        },
        "message": "moltbook auto post completed",
    }
    (notif_dir / "human_notifications.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    from hg_core.task_graph.social_outbound_learning import audit_recent_outbound

    audit = audit_recent_outbound(tmp_path, since_hours=72, platform="moltbook")
    assert audit["lessons_found"] >= 1
    tool_audit = ntt.run_task_tool("lifecycle.audit_recent_outbound", {"since_hours": 72, "platform": "moltbook"})
    assert tool_audit is not None
    dry = ntt.run_task_tool(
        "lifecycle.record_outbound_lessons",
        {"candidates": audit["candidates"], "dry_run": True},
    )
    assert dry is not None
    assert dry["outputs"]["recorded_ids"] == []
    assert len(dry["outputs"]["skipped"]) >= 1
