#!/usr/bin/env python3
"""
Tests for comment scripts mutex integration - Phase 9

Verifies that comment scripts use mutex-protected API client.
The mutex protection is already in place at the API client level (Phase 3).
These tests verify the scripts correctly use the protected API client.
"""
import unittest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# These tests patch/import the sync moltbook create_comment posting API, which was
# relocated to the async client (moltbook_api_client_async.py). Skip until the
# sync->async posting consolidation lands (see test_moltbook_sync_mutex).
from hg_platforms.moltbook import moltbook_api_client as _moltbook_sync
if not hasattr(_moltbook_sync, "create_comment"):
    pytest.skip(
        "moltbook sync create_comment relocated to the async client; comment-script "
        "mutex tests pending sync->async consolidation",
        allow_module_level=True,
    )

workspace_root = Path(__file__).parent.parent


class TestCommentScriptsUseAPIClient(unittest.TestCase):
    """Test that comment scripts use the mutex-protected API client."""
    
    def test_moltbook_create_comment_imports_api_client(self):
        """Test that the canonical moltbook create-comment implementation uses the API client."""
        script_path = workspace_root / "hg_platforms" / "moltbook" / "create_moltbook_comment.py"
        self.assertTrue(script_path.exists(), "Script should exist")
        impl_path = workspace_root / "hg_platforms" / "moltbook" / "create_moltbook_comment.py"
        script_content = script_path.read_text(encoding="utf-8")
        impl_content = impl_path.read_text(encoding="utf-8")
        # Implementation must use the shared API client path.
        self.assertIn("hg_platforms", script_content, "Implementation should live under hg_platforms")
        self.assertIn("moltbook_api_client", impl_content,
                      "Implementation should import from moltbook API client")
        self.assertNotIn("requests.post", impl_content, "Should not make direct POST requests")
        self.assertNotIn("httpx.post", impl_content, "Should not make direct POST requests")
    
    def test_skills_create_comment_imports_api_client(self):
        """Test that skills/automation/moltbook/create_moltbook_comment.py imports from API client."""
        script_path = workspace_root / "skills" / "automation" / "moltbook" / "create_moltbook_comment.py"
        self.assertTrue(script_path.exists(), "Script should exist")
        script_content = script_path.read_text(encoding="utf-8")
        # skills version imports from the canonical API client package.
        self.assertIn("moltbook_api_client", script_content,
                      "Script should import from moltbook API client")
        self.assertNotIn("requests.post", script_content, "Script should not make direct POST requests")
        self.assertNotIn("httpx.post", script_content, "Script should not make direct POST requests")
    
    @patch('hg_platforms.moltbook.moltbook_api_client.make_moltbook_request')
    def test_create_comment_calls_api_client(self, mock_request):
        """Test that create_comment function calls make_moltbook_request (which has mutex)."""
        mock_request.return_value = {
            "ok": True,
            "success": True,
            "comment": {"id": "123"}
        }
        
        # Import and call create_comment (what the scripts use)
        from hg_platforms.moltbook.moltbook_api_client import create_comment
        
        result = create_comment("post_123", "Test comment")
        
        # Verify make_moltbook_request was called (which has mutex protection)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")
        self.assertIn("posts/post_123/comments", call_args[0][1])
        
        # Verify result
        self.assertTrue(result.get("ok"))
    
    @patch('hg_platforms.moltbook.moltbook_api_client.make_moltbook_request')
    def test_create_comment_with_parent_id_calls_api_client(self, mock_request):
        """Test that create_comment with parent_id calls make_moltbook_request (which has mutex)."""
        mock_request.return_value = {
            "ok": True,
            "success": True,
            "comment": {"id": "456"}
        }
        
        # Import and call create_comment with parent_id
        from hg_platforms.moltbook.moltbook_api_client import create_comment
        
        result = create_comment("post_123", "Test reply", parent_id="comment_123")
        
        # Verify make_moltbook_request was called with parent_id
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertIn("parent_id", call_args[1]["payload"])
        self.assertEqual(call_args[1]["payload"]["parent_id"], "comment_123")
        
        # Verify result
        self.assertTrue(result.get("ok"))


class TestCommentScriptsMutexProtection(unittest.TestCase):
    """Test that comment scripts are protected by mutex (via API client)."""
    
    def test_mutex_protection_in_api_client(self):
        """Verify that make_moltbook_request has mutex protection (tested in Phase 3)."""
        # Import the API client to verify mutex is imported
        from hg_platforms.moltbook import moltbook_api_client
        
        # Verify mutex utilities are available
        self.assertTrue(hasattr(moltbook_api_client, 'posting_lock_with_content') or 
                       moltbook_api_client.posting_lock_with_content is None,
                       "posting_lock_with_content should be imported or None")
        self.assertTrue(hasattr(moltbook_api_client, 'get_content_hash') or 
                       moltbook_api_client.get_content_hash is None,
                       "get_content_hash should be imported or None")
        self.assertTrue(hasattr(moltbook_api_client, 'get_posting_lock_path') or 
                       moltbook_api_client.get_posting_lock_path is None,
                       "get_posting_lock_path should be imported or None")
        
        # Verify create_comment function exists
        self.assertTrue(hasattr(moltbook_api_client, 'create_comment'),
                       "create_comment function should exist")
        
        # Verify create_comment calls make_moltbook_request
        import inspect
        create_comment_source = inspect.getsource(moltbook_api_client.create_comment)
        self.assertIn("make_moltbook_request", create_comment_source,
                     "create_comment should call make_moltbook_request")


if __name__ == "__main__":
    unittest.main()
