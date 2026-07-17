#!/usr/bin/env python3
"""
Tests for Moltbook automation scripts.
Tests syntax, imports, argument parsing, and basic functionality.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

workspace_root = Path(__file__).parent.parent

import pytest
import subprocess


class TestMoltbookFeedScript:
    """Test fetch_moltbook_feed.py"""
    
    def test_script_imports(self):
        """Test that script can be imported without errors"""
        try:
            import hg_platforms.moltbook.fetch_moltbook_feed as feed_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import fetch_moltbook_feed: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "fetch_moltbook_feed.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "fetch_moltbook_feed.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Help should exit with code 0"
        assert "usage:" in result.stdout.lower() or "Fetch Moltbook" in result.stdout
    
    def test_positional_limit(self):
        """Test positional limit argument"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "fetch_moltbook_feed.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "5", "--sort", "new"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Should not fail with argument error (may fail with API/auth, but that's OK)
        assert "unrecognized arguments" not in result.stderr.lower()
        assert "error:" not in result.stderr.lower() or "limit" not in result.stderr.lower()
    
    def test_limit_flag(self):
        """Test --limit flag (new feature)"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "fetch_moltbook_feed.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--limit", "5", "--sort", "new"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Should not fail with argument error
        assert "unrecognized arguments" not in result.stderr.lower()
        assert result.returncode != 2, "Should not fail with argument parsing error"


class TestMoltbookSolveAndVerify:
    """Test solve_and_verify_challenge.py"""
    
    def test_script_imports(self):
        """Test that script can be imported"""
        try:
            import hg_platforms.moltbook.solve_and_verify_challenge as verify_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import solve_and_verify_challenge: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "solve_and_verify_challenge.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "solve_and_verify_challenge.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "solve" in result.stdout.lower()
    
    def test_utf8_encoding_setup(self):
        """Test that UTF-8 encoding is set up in implementation module"""
        # Implementation lives in hg_platforms (root script is shim)
        impl_path = workspace_root / "hg_platforms" / "moltbook" / "solve_and_verify_challenge.py"
        with open(impl_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for UTF-8 encoding fixes
            assert "encoding='utf-8'" in content or "io.TextIOWrapper" in content


class TestMoltbookEngageScript:
    """Test moltbook_engage.py"""
    
    def test_script_imports(self):
        """Test that script can be imported"""
        try:
            import hg_platforms.moltbook.moltbook_engage as engage_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import moltbook_engage: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "moltbook_engage.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_engagement_routine_class(self):
        """Test that EngagementRoutine class exists and can be instantiated"""
        try:
            from hg_platforms.moltbook.moltbook_engage import EngagementRoutine
            routine = EngagementRoutine()
            assert routine is not None
            assert hasattr(routine, 'run_engagement_routine')
        except Exception as e:
            pytest.fail(f"Failed to instantiate EngagementRoutine: {e}")

    def test_engagement_routine_records_human_notification(self, monkeypatch, tmp_path):
        from hg_platforms.moltbook.moltbook_engage import EngagementRoutine

        recorded = {}

        def _fake_record(workspace_root, **kwargs):
            recorded["workspace_root"] = workspace_root
            recorded["payload"] = kwargs
            return {"entry": {"recipient": "The Reverend"}, "notification_log": str(tmp_path / "notifications.jsonl")}

        monkeypatch.setattr("hg_platforms.moltbook.moltbook_engage.record_human_notification", _fake_record)
        monkeypatch.setattr("hg_platforms.moltbook.moltbook_engage.resolve_task_social_account_id", lambda **kwargs: "acct-moltbook")
        monkeypatch.setattr("hg_platforms.moltbook.moltbook_engage.runtime_tenant_id", lambda: "tenant-a")

        routine = EngagementRoutine(task_name="newfoundland-bayman-moltbook-engage")
        routine.comment_successes = 1
        routine.upvote_successes = 2
        routine.commented_post_ids_this_run.add("post-1")
        routine.upvoted_post_ids_this_run.add("post-2")

        routine.notify_human("engagement complete")

        assert recorded["workspace_root"] == workspace_root
        payload = recorded["payload"]
        assert payload["task_name"] == "newfoundland-bayman-moltbook-engage"
        assert payload["kind"] == "run_update"
        assert payload["message"] == "engagement complete"
        assert payload["social_account_id"] == "acct-moltbook"
        assert payload["tenant_id"] == "tenant-a"
        assert payload["summary"]["execution"]["platform"] == "moltbook"
        assert payload["summary"]["execution"]["status"] == "completed"
        assert sorted(payload["summary"]["execution"]["posts_touched"]) == ["post-1", "post-2"]

    def test_async_engage_priority_posts_are_merged_first(self):
        from hg_platforms.moltbook.moltbook_engage_async import AsyncEngagementRoutine

        merged = AsyncEngagementRoutine._merge_priority_posts(
            [
                {"id": "post-1", "title": "priority"},
                {"id": "post-2", "title": "priority-two"},
            ],
            [
                {"id": "post-2", "title": "feed-dup"},
                {"id": "post-3", "title": "feed-only"},
            ],
        )

        assert [post["id"] for post in merged] == ["post-1", "post-2", "post-3"]


class TestMoltbookCommentScripts:
    def test_vote_on_comment_help_mentions_downvote(self):
        script_path = workspace_root / "hg_platforms" / "moltbook" / "vote_on_moltbook_comment.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--comment_id" in result.stdout
        assert "downvote" in result.stdout

    def test_reply_activity_help_mentions_post_limit(self):
        script_path = workspace_root / "hg_platforms" / "moltbook" / "get_moltbook_reply_activity.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--post_limit" in result.stdout

    def test_create_comment_help_mentions_proof_flags(self):
        script_path = workspace_root / "hg_platforms" / "moltbook" / "create_moltbook_comment.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--social-account-id" in result.stdout
        assert "--task-name" in result.stdout

    def test_post_comment_help_mentions_proof_flags(self):
        script_path = workspace_root / "hg_platforms" / "moltbook" / "post_moltbook_comment.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--social-account-id" in result.stdout
        assert "--task-name" in result.stdout

    def test_persist_comment_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.moltbook.create_moltbook_comment import _persist_comment_proof
        from hg_gateway.db import get_connection

        artifact = _persist_comment_proof(
            social_account_id="acct-moltbook",
            tenant_id="tenant-a",
            task_name="newfoundland-bayman-moltbook-engage",
            post_id="post-1",
            parent_id=None,
            comment_content="hello",
            result={"comment": {"id": "comment-1"}, "needs_verification": False},
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "reply_proof"
        payload = json.loads(Path(artifact["path"]).read_text(encoding="utf-8"))
        assert payload["task_name"] == "newfoundland-bayman-moltbook-engage"
        assert payload["operational_agent_id"] == "newfoundland-bayman"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "reply_proof"
        assert row[1] == "acct-moltbook"

    def test_persist_comment_challenge_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.moltbook.create_moltbook_comment import _persist_comment_proof
        from hg_gateway.db import get_connection

        artifact = _persist_comment_proof(
            social_account_id="acct-moltbook",
            tenant_id="tenant-a",
            task_name="newfoundland-bayman-moltbook-engage",
            post_id="post-1",
            parent_id="comment-parent",
            comment_content="hello",
            result={
                "comment_id": "comment-1",
                "needs_verification": True,
                "verification_code": "verify-1",
                "challenge_raw": "what is 2 + 2?",
            },
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "challenge_proof"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "challenge_proof"
        assert row[1] == "acct-moltbook"


class TestMoltbookAutoPostScript:
    """Test moltbook_auto_post_async.py"""
    
    def test_script_imports(self):
        """Test that script can be imported"""
        try:
            import hg_platforms.moltbook.moltbook_auto_post_async as auto_post_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import moltbook_auto_post_async: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "moltbook_auto_post_async.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works (via root shim)"""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "moltbook_auto_post_async.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "auto-post" in result.stdout.lower()
        assert "--social-account-id" in result.stdout
        assert "--task-name" in result.stdout
    
    def test_utf8_encoding_setup(self):
        """Test that UTF-8 encoding is set up in implementation module"""
        impl_path = workspace_root / "hg_platforms" / "moltbook" / "moltbook_auto_post_async.py"
        with open(impl_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "encoding='utf-8'" in content or "io.TextIOWrapper" in content

    def test_persist_post_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.moltbook.moltbook_auto_post_async import _persist_post_proof
        from hg_gateway.db import get_connection

        artifact = _persist_post_proof(
            social_account_id="acct-moltbook",
            tenant_id="tenant-a",
            task_name="newfoundland-bayman-moltbook-auto-post",
            submolt="general",
            title="Test title",
            result={
                "ok": True,
                "post_id": "post-1",
                "post_url": "https://moltbook.example/post-1",
                "needs_verification": False,
            },
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "post_proof"
        payload = json.loads(Path(artifact["path"]).read_text(encoding="utf-8"))
        assert payload["task_name"] == "newfoundland-bayman-moltbook-auto-post"
        assert payload["operational_agent_id"] == "newfoundland-bayman"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "post_proof"
        assert row[1] == "acct-moltbook"

    def test_persist_challenge_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.moltbook.moltbook_auto_post_async import _persist_post_proof
        from hg_gateway.db import get_connection

        artifact = _persist_post_proof(
            social_account_id="acct-moltbook",
            tenant_id="tenant-a",
            task_name="newfoundland-bayman-moltbook-auto-post",
            submolt="general",
            title="Test title",
            result={
                "ok": True,
                "post_id": "post-1",
                "post_url": "https://moltbook.example/post-1",
                "needs_verification": True,
                "verification_code": "abc123",
                "challenge_raw": "what is 2 + 2?",
            },
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "challenge_proof"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "challenge_proof"
        assert row[1] == "acct-moltbook"


class TestMoltbookAPIClient:
    """Test moltbook_api_client.py functions"""
    
    def test_imports(self):
        """Test that API client can be imported"""
        try:
            from hg_platforms.moltbook.moltbook_api_client import (
                get_feed,
                format_verification_answer,
                parse_answer_format_from_response,
                get_recent_reply_activity,
                downvote_comment,
            )
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import API client functions: {e}")
    
    def test_format_verification_answer(self):
        """Test verification answer formatting"""
        from hg_platforms.moltbook.moltbook_api_client import format_verification_answer
        
        # Test integer input
        result = format_verification_answer(47)
        assert result == "47.00"
        
        # Test float input
        result = format_verification_answer(47.5)
        assert result == "47.50"
        
        # Test string input
        result = format_verification_answer("28")
        assert result == "28.00"
        
        # Test with custom decimal places
        result = format_verification_answer(37, decimal_places=3)
        assert result == "37.000"

    def test_get_recent_reply_activity_classifies_direct_and_nested_replies(self, monkeypatch):
        from hg_platforms.moltbook import moltbook_api_client as client

        monkeypatch.setattr(
            client,
            "get_agent_profile",
            lambda agent_name=None: {
                "agent": {"name": "Bayman"},
                "recentPosts": [{"id": "post-1", "title": "Harbor log"}],
            },
        )
        monkeypatch.setattr(
            client,
            "get_comments",
            lambda post_id, sort="new": {
                "comments": [
                    {
                        "id": "comment-1",
                        "content": "first reply",
                        "author": {"name": "Visitor"},
                    },
                    {
                        "id": "comment-2",
                        "content": "my reply",
                        "author": {"name": "Bayman"},
                        "parent_id": "comment-1",
                    },
                    {
                        "id": "comment-3",
                        "content": "follow-up to your reply",
                        "author": {"name": "Dockside"},
                        "parent_id": "comment-2",
                    },
                ]
            },
        )

        result = client.get_recent_reply_activity(post_limit=5)
        assert result["ok"] is True
        data = result["data"]
        assert data["reply_to_post_count"] == 1
        assert data["reply_to_reply_count"] == 1
        interaction_types = {item["interaction_type"] for item in data["items"] if item.get("comment_id")}
        assert interaction_types == {"reply_to_post", "reply_to_reply"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
