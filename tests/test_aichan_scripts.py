#!/usr/bin/env python3
"""
Tests for aichan.lol automation scripts.
Tests syntax, imports, argument parsing, and basic functionality.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

import pytest

workspace_root = Path(__file__).parent.parent
import subprocess


class TestAichanAutoPostScript:
    """Test aichan_auto_post_async.py"""
    
    def test_script_imports(self):
        """Test that script can be imported without errors"""
        try:
            import aichan.aichan_auto_post_async as auto_post_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import aichan_auto_post_async: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "aichan" / "aichan_auto_post_async.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works"""
        script_path = workspace_root / "aichan" / "aichan_auto_post_async.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        assert result.returncode == 0, "Help should exit with code 0"
        if result.stdout:
            assert "usage:" in result.stdout.lower() or "auto-post" in result.stdout.lower() or "subject_file" in result.stdout.lower()
    
    def test_file_arguments(self):
        """Test --subject_file and --body_file argument parsing"""
        script_path = workspace_root / "aichan" / "aichan_auto_post_async.py"
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test Subject")
            temp_subject_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test Body")
            temp_body_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--board", "b", "--subject_file", temp_subject_path, "--body_file", temp_body_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Should not fail with argument parsing error
            assert "unrecognized arguments" not in result.stderr.lower()
            # May fail with rate limit or API, but that's OK for this test
        finally:
            os.unlink(temp_subject_path)
            os.unlink(temp_body_path)
    
    def test_summary_only_flag(self):
        """Test --summary_only flag"""
        script_path = workspace_root / "aichan" / "aichan_auto_post_async.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.stdout:
            assert "--summary_only" in result.stdout or "--summary-only" in result.stdout or "summary" in result.stdout.lower()


class TestAichanListBoardsScript:
    """Test list_aichan_boards.py"""
    
    def test_script_imports(self):
        """Test that script can be imported"""
        try:
            import aichan.list_aichan_boards as list_boards_script
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import list_aichan_boards: {e}")
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "aichan" / "list_aichan_boards.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_script_runs(self):
        """Test that script can run (may fail with API, but should not fail with syntax)"""
        script_path = workspace_root / "aichan" / "list_aichan_boards.py"
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


class TestAichanListThreadsScript:
    """Test list_aichan_threads.py"""
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "aichan" / "list_aichan_threads.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestAichanReplyScript:
    """Test reply_to_aichan_thread.py"""
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "aichan" / "reply_to_aichan_thread.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_help_output(self):
        """Test --help flag works"""
        script_path = workspace_root / "aichan" / "reply_to_aichan_thread.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert "usage:" in result.stdout.lower() or "reply" in result.stdout.lower()


class TestAichanAPIClient:
    """Test aichan_api_client.py functions"""
    
    def test_imports(self):
        """Test that API client can be imported"""
        try:
            from aichan.aichan_api_client import (
                list_boards,
                list_threads,
                get_thread,
                create_thread,
                reply_to_thread,
                health_check
            )
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import API client functions: {e}")
    
    def test_list_boards(self):
        """Test list_boards function"""
        from aichan.aichan_api_client import list_boards
        
        boards = list_boards()
        assert isinstance(boards, list)
        assert len(boards) > 0
        assert all("slug" in board and "name" in board for board in boards)


class TestAichanGetThreadScript:
    """Test get_aichan_thread.py"""
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "aichan" / "get_aichan_thread.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestAichanCreateThreadScript:
    """Test create_aichan_thread.py"""
    
    def test_script_syntax(self):
        """Test that script has valid Python syntax"""
        script_path = workspace_root / "aichan" / "create_aichan_thread.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
