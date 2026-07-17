#!/usr/bin/env python3
"""
Tests for 4claw automation scripts.
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


class TestFourclawAutoPostScript:
    """Test fourclaw_auto_post.py"""
    
    def test_script_imports(self):
        """Test that script can be imported without errors"""
        try:
            import hg_platforms.fourclaw.fourclaw_auto_post as auto_post_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import fourclaw_auto_post: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "fourclaw_auto_post.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "fourclaw_auto_post.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        assert result.returncode == 0, "Help should exit with code 0"
        if result.stdout:
            assert "usage:" in result.stdout.lower() or "auto-post" in result.stdout.lower() or "json" in result.stdout.lower()
    
    def test_json_argument(self):
        """Test --json argument parsing"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "fourclaw_auto_post.py"
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_json = {
                "board": "b",
                "title": "Test Thread",
                "content": "Test content"
            }
            json.dump(test_json, f)
            temp_json_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--json", temp_json_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Should not fail with argument parsing error
            assert "unrecognized arguments" not in result.stderr.lower()
            # May fail with rate limit or auth, but that's OK for this test
        finally:
            os.unlink(temp_json_path)
    
    def test_summary_only_flag(self):
        """Test --summary_only flag"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "fourclaw_auto_post.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.stdout:
            assert "--summary_only" in result.stdout or "--summary-only" in result.stdout or "summary" in result.stdout.lower()


class TestFourclawListBoardsScript:
    """Test list_fourclaw_boards.py"""
    
    def test_script_imports(self):
        """Test that script can be imported"""
        try:
            import hg_platforms.fourclaw.list_fourclaw_boards as list_boards_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import list_fourclaw_boards: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "list_fourclaw_boards.py"
        if not script_path.exists():
            # Try skills/automation path
            script_path = workspace_root / "skills" / "automation" / "fourclaw" / "list_fourclaw_boards.py"
        
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_script_runs(self):
        """Test that script can run (may fail with API/auth, but should not fail with syntax)"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "list_fourclaw_boards.py"
        if not script_path.exists():
            script_path = workspace_root / "skills" / "automation" / "fourclaw" / "list_fourclaw_boards.py"
        
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Should not fail with syntax error
            assert "SyntaxError" not in result.stderr
            assert "IndentationError" not in result.stderr


class TestFourclawListThreadsScript:
    """Test list_fourclaw_threads.py"""
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "list_fourclaw_threads.py"
        if not script_path.exists():
            script_path = workspace_root / "skills" / "automation" / "fourclaw" / "list_fourclaw_threads.py"
        
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestFourclawReplyScript:
    """Test reply_to_fourclaw_thread.py"""
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "reply_to_fourclaw_thread.py"
        if not script_path.exists():
            script_path = workspace_root / "skills" / "automation" / "fourclaw" / "reply_to_fourclaw_thread.py"
        
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works"""
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "reply_to_fourclaw_thread.py"
        if not script_path.exists():
            script_path = workspace_root / "skills" / "automation" / "fourclaw" / "reply_to_fourclaw_thread.py"
        
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert "usage:" in result.stdout.lower() or "reply" in result.stdout.lower()
            assert "--task-name" in result.stdout
            assert "--social-account-id" in result.stdout

    def test_persist_reply_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.fourclaw.reply_to_fourclaw_thread import _persist_reply_proof
        from hg_gateway.db import get_connection

        artifact = _persist_reply_proof(
            social_account_id="acct-fourclaw",
            tenant_id="tenant-a",
            task_name="newfoundland-bayman-fourclaw-engage",
            thread_id="thread-1",
            content="reply text",
            result={"reply_id": "reply-1", "thread_url": "https://www.4claw.org/t/thread-1"},
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "reply_proof"
        payload = json.loads(Path(artifact["path"]).read_text(encoding="utf-8"))
        assert payload["task_name"] == "newfoundland-bayman-fourclaw-engage"
        assert payload["operational_agent_id"] == "newfoundland-bayman"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "reply_proof"
        assert row[1] == "acct-fourclaw"


class TestFourclawRegisterScript:
    def test_register_script_help_mentions_social_account_id(self):
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "register_fourclaw_agent.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--social-account-id" in result.stdout
        assert "--task-name" in result.stdout

    def test_persist_registration_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.fourclaw.register_fourclaw_agent import _persist_registration_proof
        from hg_gateway.db import get_connection

        artifact = _persist_registration_proof(
            social_account_id="acct-fourclaw",
            tenant_id="tenant-a",
            result={"agent": {"name": "bayman", "url": "https://4claw.example/bayman"}},
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "registration_proof"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "registration_proof"
        assert row[1] == "acct-fourclaw"


class TestFourclawAsyncProofs:
    def test_async_auto_post_help_mentions_proof_flags(self):
        script_path = workspace_root / "hg_platforms" / "fourclaw" / "fourclaw_auto_post_async.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--social-account-id" in result.stdout
        assert "--task-name" in result.stdout

    def test_auto_post_persist_post_proof_writes_account_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_platforms.fourclaw.fourclaw_auto_post_async import _persist_post_proof
        from hg_gateway.db import get_connection

        artifact = _persist_post_proof(
            social_account_id="acct-fourclaw",
            tenant_id="tenant-a",
            task_name="newfoundland-bayman-fourclaw-auto-post",
            board="milady",
            title="Thread title",
            result={
                "ok": True,
                "thread_id": "thread-1",
                "thread_url": "https://4claw.example/t/thread-1",
            },
        )
        assert artifact is not None
        assert artifact["artifact_type"] == "post_proof"
        payload = json.loads(Path(artifact["path"]).read_text(encoding="utf-8"))
        assert payload["task_name"] == "newfoundland-bayman-fourclaw-auto-post"
        assert payload["operational_agent_id"] == "newfoundland-bayman"
        with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
            row = conn.execute(
                "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
            ).fetchone()
        assert row is not None
        assert row[0] == "post_proof"
        assert row[1] == "acct-fourclaw"


class TestFourclawAPIClient:
    """Test fourclaw_api_client.py functions"""
    
    def test_imports(self):
        """Test that API client can be imported"""
        try:
            from hg_platforms.fourclaw.fourclaw_api_client import (
                create_thread,
                find_workspace_root
            )
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import API client functions: {e}")
    
    def test_find_workspace_root(self):
        """Test find_workspace_root function"""
        from hg_platforms.fourclaw.fourclaw_api_client import find_workspace_root
        
        workspace = find_workspace_root()
        assert workspace is not None
        assert isinstance(workspace, Path)
        assert workspace.exists()


class TestFourclawContentHistory:
    """Test fourclaw_content_history.py"""
    
    def test_imports(self):
        """Test that content history can be imported"""
        try:
            from hg_platforms.fourclaw.fourclaw_content_history import (
                check_content_hash,
                add_content_to_history
            )
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import content history functions: {e}")


class TestFourclawSVGValidator:
    """Test svg_validator.py"""
    
    def test_imports(self):
        """Test that SVG validator can be imported"""
        try:
            from hg_platforms.fourclaw.svg_validator import (
                validate_and_fix_svg,
                create_svg_validation_report
            )
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import SVG validator functions: {e}")
    
    def test_validate_simple_svg(self):
        """Test SVG validation with a simple valid SVG"""
        from hg_platforms.fourclaw.svg_validator import validate_and_fix_svg
        
        simple_svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        fixed, is_valid, error = validate_and_fix_svg(simple_svg)
        
        assert isinstance(is_valid, bool)
        assert isinstance(error, (str, type(None)))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
