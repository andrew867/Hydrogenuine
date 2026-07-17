from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hg_core.task_graph.social_outbound_learning import lessons_store_path, load_active_lessons


def test_backfill_creates_expected_lesson_kinds(tmp_path: Path):
    notif_dir = tmp_path / "memory/automation/notifications"
    notif_dir.mkdir(parents=True)
    fixture = Path("tests/fixtures/social_outbound/notification_incident_20260611.jsonl").read_text(encoding="utf-8")
    (notif_dir / "human_notifications.jsonl").write_text(fixture, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/social/backfill_outbound_lessons.py",
            "--workspace",
            str(tmp_path),
            "--since",
            "2026-06-10T00:00:00Z",
        ],
        cwd=Path("."),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    stats = json.loads(proc.stdout)
    assert stats["recorded"] >= 1
    lessons = load_active_lessons(tmp_path, limit=50)
    kinds = {row.get("kind") for row in lessons}
    assert "structured_decision_leak" in kinds or "operator_leak" in kinds


def test_backfill_idempotent(tmp_path: Path):
    notif_dir = tmp_path / "memory/automation/notifications"
    notif_dir.mkdir(parents=True)
    fixture = Path("tests/fixtures/social_outbound/notification_incident_20260611.jsonl").read_text(encoding="utf-8")
    (notif_dir / "human_notifications.jsonl").write_text(fixture, encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/social/backfill_outbound_lessons.py",
        "--workspace",
        str(tmp_path),
        "--since",
        "2026-06-10T00:00:00Z",
    ]
    subprocess.run(cmd, cwd=Path("."), check=True, capture_output=True, text=True)
    count_first = len(load_active_lessons(tmp_path, limit=100))
    subprocess.run(cmd, cwd=Path("."), check=True, capture_output=True, text=True)
    count_second = len(load_active_lessons(tmp_path, limit=100))
    assert count_second == count_first


def test_backfill_since_filter(tmp_path: Path):
    notif_dir = tmp_path / "memory/automation/notifications"
    notif_dir.mkdir(parents=True)
    rows = [
        {"timestamp": "2026-06-09T00:00:00Z", "task_name": "moltbook-engage", "summary": {"external_calls": 1, "body_snippet": "autonomous engage"}},
        {"timestamp": "2026-06-11T03:37:00Z", "task_name": "moltbook-auto-post", "summary": {"external_calls": 1, "body_snippet": '{"action": "research"}'}},
    ]
    (notif_dir / "human_notifications.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/social/backfill_outbound_lessons.py",
            "--workspace",
            str(tmp_path),
            "--since",
            "2026-06-11T00:00:00Z",
        ],
        cwd=Path("."),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    lessons = load_active_lessons(tmp_path, limit=20)
    assert lessons
    assert all("2026-06-11" in str(row.get("recorded_at") or "") for row in lessons)
    assert lessons_store_path(tmp_path).is_file()
