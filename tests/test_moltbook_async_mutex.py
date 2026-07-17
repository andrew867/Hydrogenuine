#!/usr/bin/env python3
"""
Tests for moltbook_api_client_async.py mutex integration - Phase 2

Tests POST request mutex protection, concurrent requests, and error handling.
"""
import unittest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any

from hg_platforms.moltbook.moltbook_api_client_async import (
    MoltbookAsyncClient,
    AsyncMutexManager
)


class TestAsyncMutexManager(unittest.IsolatedAsyncioTestCase):
    """Test AsyncMutexManager helper class."""
    
    def test_async_mutex_manager_import(self):
        """Test that AsyncMutexManager can be imported."""
        self.assertTrue(AsyncMutexManager is not None)
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.posting_lock_with_content')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.asyncio.to_thread')
    async def test_async_mutex_acquire_release(self, mock_to_thread, mock_lock):
        """Test that AsyncMutexManager properly acquires and releases lock."""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_lock.return_value = mock_context
        
        # Mock asyncio.to_thread to call the function directly (for testing)
        async def mock_to_thread_impl(func):
            # Call function directly without recursion
            return func()
        mock_to_thread.side_effect = mock_to_thread_impl
        
        lock_path = Path("/tmp/test.lock")
        content_hash = "test_hash_123"
        
        async with AsyncMutexManager(lock_path, content_hash):
            # Lock should be acquired
            mock_lock.assert_called_once()
            mock_context.__enter__.assert_called_once()
        
        # Lock should be released
        mock_context.__exit__.assert_called_once()


class TestMoltbookAsyncClientMutex(unittest.IsolatedAsyncioTestCase):
    """Test MoltbookAsyncClient with mutex integration."""
    
    def setUp(self):
        """Set up test client."""
        # Mock API key
        with patch('hg_platforms.moltbook.moltbook_api_client_async.load_api_key', return_value="test_api_key"):
            self.client = MoltbookAsyncClient(api_key="test_api_key")
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.httpx.AsyncClient')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.AsyncMutexManager')
    async def test_post_request_with_mutex(self, mock_mutex_manager, mock_lock_path, mock_get_hash, mock_client_class):
        """Test that POST requests use mutex."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        mock_mutex = MagicMock()
        mock_mutex.__aenter__ = AsyncMock(return_value=mock_mutex)
        mock_mutex.__aexit__ = AsyncMock(return_value=None)
        mock_mutex_manager.return_value = mock_mutex
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "post": {"id": "123"}}
        
        mock_client_instance = MagicMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        # Make POST request
        result = await self.client._request("POST", "/posts", json={"title": "Test"})
        
        # Verify mutex was used
        mock_get_hash.assert_called_once()
        mock_lock_path.assert_called_once()
        mock_mutex_manager.assert_called_once()
        mock_mutex.__aenter__.assert_called_once()
        mock_mutex.__aexit__.assert_called_once()
        
        # Verify request was made
        mock_client_instance.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result["_status_code"], 201)
        self.assertTrue(result.get("success"))
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.httpx.AsyncClient')
    async def test_get_request_without_mutex(self, mock_client_class):
        """Test that GET requests don't use mutex."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        mock_client_instance = MagicMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        # Make GET request
        result = await self.client._request("GET", "/posts")
        
        # Verify request was made
        mock_client_instance.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result["_status_code"], 200)
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.httpx.AsyncClient')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.AsyncMutexManager')
    async def test_post_request_duplicate_blocked(self, mock_mutex_manager, mock_lock_path, mock_get_hash, mock_client_class):
        """Test that duplicate POST requests are blocked."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise ValueError (duplicate content)
        mock_mutex = MagicMock()
        mock_mutex.__aenter__ = AsyncMock(side_effect=ValueError("Content hash already being posted"))
        mock_mutex_manager.return_value = mock_mutex
        
        # Make POST request
        result = await self.client._request("POST", "/posts", json={"title": "Test"})
        
        # Verify mutex was attempted
        mock_get_hash.assert_called_once()
        mock_mutex_manager.assert_called_once()
        
        # Verify request was blocked
        self.assertIn("error", result)
        self.assertEqual(result.get("error_code"), "DUPLICATE_CONTENT")
        self.assertEqual(result.get("_exception"), "ValueError")
        
        # Verify HTTP request was NOT made
        mock_client_class.assert_not_called()
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.httpx.AsyncClient')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.AsyncMutexManager')
    async def test_post_request_mutex_timeout(self, mock_mutex_manager, mock_lock_path, mock_get_hash, mock_client_class):
        """Test that mutex timeout is handled gracefully."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise TimeoutError
        mock_mutex = MagicMock()
        mock_mutex.__aenter__ = AsyncMock(side_effect=TimeoutError("Could not acquire lock"))
        mock_mutex_manager.return_value = mock_mutex
        
        # Make POST request
        result = await self.client._request("POST", "/posts", json={"title": "Test"})
        
        # Verify request was blocked due to timeout
        self.assertIn("error", result)
        self.assertEqual(result.get("error_code"), "MUTEX_TIMEOUT")
        self.assertEqual(result.get("_exception"), "TimeoutError")
        
        # Verify HTTP request was NOT made
        mock_client_class.assert_not_called()
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.httpx.AsyncClient')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_content_hash')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.get_posting_lock_path')
    @patch('hg_platforms.moltbook.moltbook_api_client_async.AsyncMutexManager')
    async def test_post_request_mutex_error_fallback(self, mock_mutex_manager, mock_lock_path, mock_get_hash, mock_client_class):
        """Test that mutex errors fall back to making request without mutex."""
        # Setup mocks
        mock_get_hash.return_value = "test_hash_123"
        mock_lock_path.return_value = Path("/tmp/test.lock")
        
        # Mock mutex to raise generic exception
        mock_mutex = MagicMock()
        mock_mutex.__aenter__ = AsyncMock(side_effect=RuntimeError("Mutex error"))
        mock_mutex_manager.return_value = mock_mutex
        
        # Mock HTTP response (should still be made)
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        
        mock_client_instance = MagicMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        # Make POST request
        result = await self.client._request("POST", "/posts", json={"title": "Test"})
        
        # Verify request was still made (fallback)
        mock_client_instance.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result["_status_code"], 201)
    
    @patch('hg_platforms.moltbook.moltbook_api_client_async.httpx.AsyncClient')
    async def test_post_request_without_json_no_mutex(self, mock_client_class):
        """Test that POST requests without JSON payload don't use mutex."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        mock_client_instance = MagicMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        # Make POST request without JSON
        result = await self.client._request("POST", "/posts/123/upvote")
        
        # Verify request was made
        mock_client_instance.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result["_status_code"], 200)


class TestMoltbookAsyncClientCreatePost(unittest.IsolatedAsyncioTestCase):
    """Test create_post method with mutex."""
    
    def setUp(self):
        """Set up test client."""
        with patch('hg_platforms.moltbook.moltbook_api_client_async.load_api_key', return_value="test_api_key"):
            self.client = MoltbookAsyncClient(api_key="test_api_key")
    
    @patch.object(MoltbookAsyncClient, '_request')
    async def test_create_post_uses_mutex(self, mock_request):
        """Test that create_post uses mutex through _request."""
        mock_request.return_value = {
            "success": True,
            "post": {"id": "123"},
            "_status_code": 201
        }
        
        result = await self.client.create_post("general", "Test Title", "Test Content")
        
        # Verify _request was called with POST and JSON payload
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")  # method
        self.assertEqual(call_args[0][1], "/posts")  # endpoint
        self.assertIn("json", call_args[1])  # kwargs should have json
        
        # Verify payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["submolt_name"], "general")
        self.assertEqual(payload["title"], "Test Title")
        self.assertEqual(payload["content"], "Test Content")

    @patch.object(MoltbookAsyncClient, "_request")
    async def test_create_post_falls_back_to_legacy_payload(self, mock_request):
        """If server rejects submolt_name, client retries once with legacy submolt payload."""
        mock_request.side_effect = [
            {
                "error": 'HTTP 400: {"message":["property submolt_name should not exist"]}',
                "_status_code": 400,
                "_raw_response": '{"message":["property submolt_name should not exist"]}',
            },
            {"success": True, "post": {"id": "123"}, "_status_code": 201},
        ]

        result = await self.client.create_post("general", "Test Title", "Test Content")
        self.assertTrue(result.get("success"))
        self.assertEqual(mock_request.call_count, 2)

        first_payload = mock_request.call_args_list[0][1]["json"]
        self.assertEqual(first_payload["submolt_name"], "general")
        self.assertNotIn("submolt", first_payload)

        second_payload = mock_request.call_args_list[1][1]["json"]
        self.assertEqual(second_payload["submolt"], "general")


if __name__ == "__main__":
    unittest.main()
