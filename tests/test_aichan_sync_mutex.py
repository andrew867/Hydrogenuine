#!/usr/bin/env python3
"""
Tests for aichan_api_client.py mutex integration - Phase 8

Tests POST request mutex protection, concurrent requests, and error handling.
"""
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock requests before importing
sys.modules['requests'] = MagicMock()

from aichan.aichan_api_client import (
    make_aichan_request,
    create_thread,
    reply_to_thread
)


class TestAichanSyncClientMutex(unittest.TestCase):
    """Test aichan_api_client.py with mutex integration."""
    
    @patch('aichan.aichan_api_client.requests.post')
    @patch('aichan.aichan_api_client.get_content_hash')
    @patch('aichan.aichan_api_client.get_posting_lock_path')
    @patch('aichan.aichan_api_client.posting_lock_with_content')
    def test_post_request_with_mutex(self, mock_lock, mock_lock_path, mock_get_hash, mock_post):
        """Test that POST requests use mutex."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_lock.return_value = mock_context
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": "/b/res/123.html"}
        mock_response.text = ""
        mock_post.return_value = mock_response
        
        # Make POST request
        result = make_aichan_request("POST", "/post.php", data={"board": "b", "body": "Test", "post": "New Topic"})
        
        # Verify mutex was used
        mock_get_hash.assert_called_once()
        mock_lock_path.assert_called_once()
        mock_lock.assert_called_once()
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        
        # Verify request was made
        mock_post.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("thread_id"), "123")
    
    @patch('aichan.aichan_api_client.requests.get')
    def test_get_request_without_mutex(self, mock_get):
        """Test that GET requests don't use mutex."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"threads": []}]
        mock_response.text = "[]"
        mock_get.return_value = mock_response
        
        # Make GET request
        result = make_aichan_request("GET", "/b/threads.json")
        
        # Verify request was made
        mock_get.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("ok"))
    
    @patch('aichan.aichan_api_client.requests.post')
    @patch('aichan.aichan_api_client.get_content_hash')
    @patch('aichan.aichan_api_client.get_posting_lock_path')
    @patch('aichan.aichan_api_client.posting_lock_with_content')
    def test_post_request_duplicate_blocked(self, mock_lock, mock_lock_path, mock_get_hash, mock_post):
        """Test that duplicate POST requests are blocked."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise ValueError (duplicate content)
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=ValueError("Content hash already being posted"))
        mock_lock.return_value = mock_context
        
        # Make POST request
        result = make_aichan_request("POST", "/post.php", data={"board": "b", "body": "Test"})
        
        # Verify request was blocked
        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("error_code"), "DUPLICATE_CONTENT")
        self.assertIn("Duplicate POST request prevented", result.get("error"))
    
    @patch('aichan.aichan_api_client.requests.post')
    @patch('aichan.aichan_api_client.get_content_hash')
    @patch('aichan.aichan_api_client.get_posting_lock_path')
    @patch('aichan.aichan_api_client.posting_lock_with_content')
    def test_post_request_mutex_timeout(self, mock_lock, mock_lock_path, mock_get_hash, mock_post):
        """Test that mutex timeout is handled gracefully."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise TimeoutError
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=TimeoutError("Could not acquire lock"))
        mock_lock.return_value = mock_context
        
        # Make POST request
        result = make_aichan_request("POST", "/post.php", data={"board": "b", "body": "Test"})
        
        # Verify request was blocked due to timeout
        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("error_code"), "MUTEX_TIMEOUT")
        self.assertIn("Could not acquire posting lock", result.get("error"))
    
    @patch('aichan.aichan_api_client.requests.post')
    @patch('aichan.aichan_api_client.get_content_hash')
    @patch('aichan.aichan_api_client.get_posting_lock_path')
    @patch('aichan.aichan_api_client.posting_lock_with_content')
    def test_post_request_mutex_error_fallback(self, mock_lock, mock_lock_path, mock_get_hash, mock_post):
        """Test that mutex errors fall back to making request without mutex."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise generic exception
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=RuntimeError("Mutex error"))
        mock_lock.return_value = mock_context
        
        # Mock HTTP response (should still be made)
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": "/b/res/123.html"}
        mock_response.text = ""
        mock_post.return_value = mock_response
        
        # Make POST request
        result = make_aichan_request("POST", "/post.php", data={"board": "b", "body": "Test", "post": "New Topic"})
        
        # Verify request was still made (fallback)
        mock_post.assert_called_once()
        
        # Verify result
        self.assertTrue(result.get("ok"))
    
    @patch('aichan.aichan_api_client.requests.post')
    def test_post_request_without_data_no_mutex(self, mock_post):
        """Test that POST requests without data don't use mutex."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {}
        mock_response.text = ""
        mock_post.return_value = mock_response
        
        # Make POST request
        result = make_aichan_request("POST", "/post.php", data=None)
        
        # Verify result
        self.assertTrue(result.get("ok"))


class TestCreateThreadMutex(unittest.TestCase):
    """Test create_thread function with mutex."""
    
    @patch('aichan.aichan_api_client.make_aichan_request')
    @patch('aichan.aichan_api_client.get_content_hash')
    def test_create_thread_uses_mutex(self, mock_get_hash, mock_request):
        """Test that create_thread uses mutex through make_aichan_request."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_request.return_value = {
            "ok": True,
            "status_code": 302,
            "thread_id": "123",
            "location": "/b/res/123.html"
        }
        
        # Create thread
        result = create_thread("b", "Test Subject", "Test Body")
        
        # Verify mutex was used (make_aichan_request was called with POST)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")
        
        # Verify result
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("thread_id"), "123")


class TestReplyToThreadMutex(unittest.TestCase):
    """Test reply_to_thread function with mutex."""
    
    @patch('aichan.aichan_api_client.make_aichan_request')
    @patch('aichan.aichan_api_client.get_content_hash')
    def test_reply_to_thread_uses_mutex(self, mock_get_hash, mock_request):
        """Test that reply_to_thread uses mutex through make_aichan_request."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_request.return_value = {
            "ok": True,
            "status_code": 302
        }
        
        # Reply to thread
        result = reply_to_thread("b", "123", "Test reply")
        
        # Verify mutex was used (make_aichan_request was called with POST)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")
        
        # Verify result
        self.assertTrue(result.get("ok"))


if __name__ == "__main__":
    unittest.main()
