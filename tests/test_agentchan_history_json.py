#!/usr/bin/env python3
import json
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentchan import agentchan_auto_post_async as auto_post
from agentchan import agentchan_engage_async as engage


def _make_test_workspace() -> Path:
    root = Path.cwd() / ".tmp_agentchan_tests"
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / f"ws_{uuid.uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def test_auto_post_load_repairs_invalid_json(monkeypatch):
    workspace = _make_test_workspace()
    monkeypatch.setattr(auto_post, "find_workspace_root", lambda: workspace)
    history_file = workspace / "memory" / "automation" / "automation-agentchan-auto-post" / "posts.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        '{\n  "posts": [\n    {"subject":"it\\\'s valid text but invalid json escape"}\n  ]\n}\n',
        encoding="utf-8",
    )

    try:
        posts = auto_post.load_post_history()
        assert len(posts) == 1
        assert posts[0]["subject"] == "it's valid text but invalid json escape"

        parsed = json.loads(history_file.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)
        assert isinstance(parsed.get("posts"), list)
        assert "last_updated" in parsed
        backups = list(history_file.parent.glob("posts.invalid-*.json.bak"))
        assert backups
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_auto_post_save_writes_canonical_wrapper(monkeypatch):
    workspace = _make_test_workspace()
    monkeypatch.setattr(auto_post, "find_workspace_root", lambda: workspace)
    try:
        auto_post.save_post_history(
            [
                {"thread_id": 1, "subject": "one"},
                {"thread_id": 2, "subject": "two"},
            ]
        )
        history_file = workspace / "memory" / "automation" / "automation-agentchan-auto-post" / "posts.json"
        parsed = json.loads(history_file.read_text(encoding="utf-8"))
        assert set(parsed.keys()) == {"posts", "last_updated"}
        assert len(parsed["posts"]) == 2
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_engage_load_repairs_invalid_json(monkeypatch):
    workspace = _make_test_workspace()
    monkeypatch.setattr(engage, "find_workspace_root", lambda: workspace)
    history_file = workspace / "memory" / "automation" / "automation-agentchan-engage" / "posts.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        '[\n  {"content":"can\\\'t parse with standard json"}\n]\n',
        encoding="utf-8",
    )

    try:
        posts = engage.load_engagement_history()
        assert len(posts) == 1
        assert posts[0]["content"] == "can't parse with standard json"
        reparsed = json.loads(history_file.read_text(encoding="utf-8"))
        assert isinstance(reparsed, list)
        backups = list(history_file.parent.glob("posts.invalid-*.json.bak"))
        assert backups
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
