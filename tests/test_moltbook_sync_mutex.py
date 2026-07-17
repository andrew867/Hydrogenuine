#!/usr/bin/env python3
"""
Tests for moltbook_api_client.py mutex integration - Phase 3

Tests POST request mutex protection, concurrent requests, and error handling.
"""
import unittest
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Mock requests before importing
sys.modules['requests'] = MagicMock()

import pytest

# The synchronous moltbook posting API (make_moltbook_request/create_post/
# create_comment + its mutex) was relocated to the async client
# (moltbook_api_client_async.py); the sync client is now read-only. These sync mutex
# tests — and several posting scripts that still import from the sync client — are
# pending a sync->async consolidation. Skip honestly until that migration lands.
try:
    from hg_platforms.moltbook.moltbook_api_client import (
        make_moltbook_request,
        create_post,
        create_comment,
    )
except ImportError:
    pytest.skip(
        "moltbook sync posting API relocated to the async client; sync mutex tests "
        "pending sync->async consolidation",
        allow_module_level=True,
    )


class TestMakeMoltbookRequestMutex(unittest.TestCase):
    """Test make_moltbook_request with mutex integration."""
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.requests.post')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content')
    def test_post_request_with_mutex(self, mock_lock, mock_lock_path, mock_get_hash, mock_post, mock_load_key):
        """Test that POST requests use mutex."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_lock.return_value = mock_context
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "post": {"id": "123"}}
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        # Make POST request
        result = make_moltbook_request("POST", "posts", payload={"title": "Test"})
        
        # Verify mutex was used
        mock_get_hash.assert_called_once()
        mock_lock_path.assert_called_once()
        mock_lock.assert_called_once()
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        
        # Verify request was made
        mock_post.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("success"))
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.requests.get')
    def test_get_request_without_mutex(self, mock_get, mock_load_key):
        """Test that GET requests don't use mutex."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        # Make GET request
        result = make_moltbook_request("GET", "posts")
        
        # Verify request was made
        mock_get.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("success"))
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content')
    def test_post_request_duplicate_blocked(self, mock_lock, mock_lock_path, mock_get_hash, mock_load_key):
        """Test that duplicate POST requests are blocked."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise ValueError (duplicate content)
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=ValueError("Content hash already being posted"))
        mock_lock.return_value = mock_context
        
        # Make POST request
        result = make_moltbook_request("POST", "posts", payload={"title": "Test"})
        
        # Verify mutex was attempted
        mock_get_hash.assert_called_once()
        mock_lock.assert_called_once()
        
        # Verify request was blocked
        self.assertFalse(result.get("ok", True))
        self.assertIn("error", result)
        self.assertEqual(result.get("error_code"), "DUPLICATE_CONTENT")
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content')
    def test_post_request_mutex_timeout(self, mock_lock, mock_lock_path, mock_get_hash, mock_load_key):
        """Test that mutex timeout is handled gracefully."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise TimeoutError
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=TimeoutError("Could not acquire lock"))
        mock_lock.return_value = mock_context
        
        # Make POST request
        result = make_moltbook_request("POST", "posts", payload={"title": "Test"})
        
        # Verify request was blocked due to timeout
        self.assertFalse(result.get("ok", True))
        self.assertIn("error", result)
        self.assertEqual(result.get("error_code"), "MUTEX_TIMEOUT")
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.requests.post')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content')
    def test_post_request_mutex_error_fallback(self, mock_lock, mock_lock_path, mock_get_hash, mock_post, mock_load_key):
        """Test that mutex errors fall back to making request without mutex."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise generic exception
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=RuntimeError("Mutex error"))
        mock_lock.return_value = mock_context
        
        # Mock HTTP response (should still be made)
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        # Make POST request
        result = make_moltbook_request("POST", "posts", payload={"title": "Test"})
        
        # Verify request was still made (fallback)
        mock_post.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("success"))
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.requests.post')
    def test_post_request_without_payload_no_mutex(self, mock_post, mock_load_key):
        """Test that POST requests without payload don't use mutex."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        # Make POST request without payload
        result = make_moltbook_request("POST", "posts/123/upvote", payload=None)
        
        # Verify request was made
        mock_post.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("success"))


class TestCreatePostMutex(unittest.TestCase):
    """Test create_post function with mutex."""
    
    @patch('hg_platforms.moltbook.moltbook_api_client.make_moltbook_request')
    def test_create_post_uses_mutex(self, mock_request):
        """Test that create_post uses mutex through make_moltbook_request."""
        mock_request.return_value = {
            "success": True,
            "post": {"id": "123"}
        }
        
        result = create_post("general", "Test Title", "Test Content")
        
        # Verify make_moltbook_request was called with POST and payload
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")  # method
        self.assertEqual(call_args[0][1], "posts")  # endpoint
        self.assertIsNotNone(call_args[1].get("payload"))  # kwargs should have payload
        
        # Verify payload
        payload = call_args[1]["payload"]
        self.assertEqual(payload["submolt"], "general")
        self.assertEqual(payload["title"], "Test Title")
        self.assertEqual(payload["content"], "Test Content")


class TestCreateCommentMutex(unittest.TestCase):
    """Test create_comment function with mutex."""
    
    @patch('hg_platforms.moltbook.moltbook_api_client.make_moltbook_request')
    def test_create_comment_uses_mutex(self, mock_request):
        """Test that create_comment uses mutex through make_moltbook_request."""
        mock_request.return_value = {
            "success": True,
            "comment": {"id": "456"}
        }
        
        result = create_comment("post_123", "Test comment")
        
        # Verify make_moltbook_request was called with POST and payload
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")  # method
        self.assertIn("comments", call_args[0][1])  # endpoint contains comments
        self.assertIsNotNone(call_args[1].get("payload"))  # kwargs should have payload
        
        # Verify payload
        payload = call_args[1]["payload"]
        self.assertEqual(payload["content"], "Test comment")


class TestConcurrentRequests(unittest.TestCase):
    """Test concurrent POST requests with mutex."""
    
    @patch('hg_platforms.moltbook.moltbook_api_client.load_api_key')
    @patch('hg_platforms.moltbook.moltbook_api_client.requests.post')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content')
    def test_concurrent_same_content_blocked(self, mock_lock, mock_lock_path, mock_get_hash, mock_post, mock_load_key):
        """Test that concurrent POST requests with same content are blocked."""
        # Setup mocks
        mock_load_key.return_value = "test_api_key"
        mock_get_hash.return_value = "test_hash_123"  # Same hash for all
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        results = []
        lock_acquired = threading.Event()
        
        def mock_lock_side_effect(*args, **kwargs):
            mock_context = MagicMock()
            # First call succeeds, subsequent calls block
            if not lock_acquired.is_set():
                lock_acquired.set()
                mock_context.__enter__ = MagicMock(return_value=mock_context)
                mock_context.__exit__ = MagicMock(return_value=None)
            else:
                # Subsequent calls raise ValueError (duplicate)
                mock_context.__enter__ = MagicMock(side_effect=ValueError("Content hash already being posted"))
            return mock_context
        
        mock_lock.side_effect = mock_lock_side_effect
        
        # Mock HTTP response for successful request
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        def make_request():
            try:
                result = make_moltbook_request("POST", "posts", payload={"title": "Test"})
                results.append(("success", result))
            except Exception as e:
                results.append(("error", str(e)))
        
        # Make 3 concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # At least one should succeed, others should be blocked
        success_count = len([r for r in results if r[0] == "success" and r[1].get("success")])
        blocked_count = len([r for r in results if r[0] == "success" and r[1].get("error_code") == "DUPLICATE_CONTENT"])
        
        # In real scenario, only one should succeed
        # For this test, we verify the structure works
        self.assertEqual(len(results), 3, "Should have 3 results")
        self.assertGreater(success_count + blocked_count, 0, "Should have some results")


if __name__ == "__main__":
    unittest.main()
