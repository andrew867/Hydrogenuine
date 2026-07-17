#!/usr/bin/env python3
"""
Tests for agentchan_api_client_async.py mutex integration - Phase 7

Tests POST request mutex protection, concurrent requests, and error handling.
"""
import unittest
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Mock httpx before importing
sys.modules['httpx'] = MagicMock()

from agentchan.agentchan_api_client_async import (
    AgentchanAsyncClient,
    AsyncMutexManager
)


class TestAsyncMutexManager(unittest.IsolatedAsyncioTestCase):
    """Test AsyncMutexManager helper class."""
    
    @patch('agentchan.agentchan_api_client_async.posting_lock_with_content')
    @patch('agentchan.agentchan_api_client_async.asyncio.to_thread')
    async def test_async_mutex_acquire_release(self, mock_to_thread, mock_lock):
        """Test that AsyncMutexManager acquires and releases lock."""
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_lock.return_value = mock_context
        
        # Mock asyncio.to_thread to call the function directly
        async def mock_to_thread_impl(func):
            return func()
        mock_to_thread.side_effect = mock_to_thread_impl
        
        lock_path = Path("/tmp/test.lock")
        content_hash = "test_hash_123"
        
        manager = AsyncMutexManager(lock_path, content_hash, timeout=5.0, max_wait=60.0)
        
        async with manager:
            self.assertTrue(manager.lock_acquired)
            mock_lock.assert_called_once()
            mock_context.__enter__.assert_called_once()
        
        mock_context.__exit__.assert_called_once()
        self.assertFalse(manager.lock_acquired)
    
    @patch('agentchan.agentchan_api_client_async.posting_lock_with_content')
    @patch('agentchan.agentchan_api_client_async.asyncio.to_thread')
    async def test_async_mutex_error_handling(self, mock_to_thread, mock_lock):
        """Test that AsyncMutexManager handles errors."""
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=ValueError("Lock error"))
        mock_lock.return_value = mock_context
        
        # Mock asyncio.to_thread to call the function directly
        async def mock_to_thread_impl(func):
            return func()
        mock_to_thread.side_effect = mock_to_thread_impl
        
        lock_path = Path("/tmp/test.lock")
        content_hash = "test_hash_123"
        
        manager = AsyncMutexManager(lock_path, content_hash, timeout=5.0, max_wait=60.0)
        
        with self.assertRaises(ValueError):
            async with manager:
                pass


class TestAgentchanAsyncClientMutex(unittest.IsolatedAsyncioTestCase):
    """Test AgentchanAsyncClient with mutex integration."""
    
    def setUp(self):
        """Set up test client."""
        # Mock JWT
        with patch('agentchan.agentchan_api_client_async.load_jwt', return_value="test_jwt"):
            self.client = AgentchanAsyncClient(jwt="test_jwt")
            # Manually set client to avoid context manager
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            self.client.client = mock_client
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    @patch('agentchan.agentchan_api_client_async.get_content_hash')
    @patch('agentchan.agentchan_api_client_async.get_posting_lock_path')
    @patch('agentchan.agentchan_api_client_async.AsyncMutexManager')
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
        mock_response.json.return_value = {"success": True, "thread": {"id": "123"}}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        # Set the client's request method to return the mock response
        self.client.client.request = AsyncMock(return_value=mock_response)
        
        # Make POST request
        result = await self.client._request("POST", "/boards/test/threads", json={"subject": "Test", "content": "Test"})
        
        # Verify mutex was used
        mock_get_hash.assert_called_once()
        mock_lock_path.assert_called_once()
        mock_mutex_manager.assert_called_once()
        mock_mutex.__aenter__.assert_called_once()
        mock_mutex.__aexit__.assert_called_once()
        
        # Verify request was made
        self.client.client.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result["_status_code"], 201)
        self.assertTrue(result.get("success"))
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    async def test_get_request_without_mutex(self, mock_client_class):
        """Test that GET requests don't use mutex."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        # Set the client's request method to return the mock response
        self.client.client.request = AsyncMock(return_value=mock_response)
        
        # Make GET request
        result = await self.client._request("GET", "/boards")
        
        # Verify request was made
        self.client.client.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result["_status_code"], 200)
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    @patch('agentchan.agentchan_api_client_async.get_content_hash')
    @patch('agentchan.agentchan_api_client_async.get_posting_lock_path')
    @patch('agentchan.agentchan_api_client_async.AsyncMutexManager')
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
        result = await self.client._request("POST", "/boards/test/threads", json={"subject": "Test"})
        
        # Verify request was blocked
        self.assertIn("error", result)
        self.assertEqual(result.get("error_code"), "DUPLICATE_CONTENT")
        self.assertEqual(result.get("_status_code"), 409)
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    @patch('agentchan.agentchan_api_client_async.get_content_hash')
    @patch('agentchan.agentchan_api_client_async.get_posting_lock_path')
    @patch('agentchan.agentchan_api_client_async.AsyncMutexManager')
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
        result = await self.client._request("POST", "/boards/test/threads", json={"subject": "Test"})
        
        # Verify request was blocked due to timeout
        self.assertIn("error", result)
        self.assertEqual(result.get("error_code"), "MUTEX_TIMEOUT")
        self.assertEqual(result.get("_status_code"), 408)
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    @patch('agentchan.agentchan_api_client_async.get_content_hash')
    @patch('agentchan.agentchan_api_client_async.get_posting_lock_path')
    @patch('agentchan.agentchan_api_client_async.AsyncMutexManager')
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
        mock_response.text = "{}"
        mock_response.headers = {}
        
        # Set the client's request method to return the mock response
        self.client.client.request = AsyncMock(return_value=mock_response)
        
        # Make POST request
        result = await self.client._request("POST", "/boards/test/threads", json={"subject": "Test"})
        
        # Verify request was still made (fallback)
        self.client.client.request.assert_called_once()
        
        # Verify result
        self.assertEqual(result.get("_status_code"), 201)
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    async def test_post_request_without_json_no_mutex(self, mock_client_class):
        """Test that POST requests without JSON don't use mutex."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        # Set the client's request method to return the mock response
        self.client.client.request = AsyncMock(return_value=mock_response)
        
        # Make POST request
        result = await self.client._request("POST", "/boards/test/threads")
        
        # Verify result
        self.assertEqual(result.get("_status_code"), 200)


class TestCreateThreadMutex(unittest.IsolatedAsyncioTestCase):
    """Test create_thread method with mutex."""
    
    def setUp(self):
        """Set up test client."""
        with patch('agentchan.agentchan_api_client_async.load_jwt', return_value="test_jwt"):
            self.client = AgentchanAsyncClient(jwt="test_jwt")
            # Manually set client to avoid context manager
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            self.client.client = mock_client
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    @patch('agentchan.agentchan_api_client_async.get_content_hash')
    @patch('agentchan.agentchan_api_client_async.get_posting_lock_path')
    @patch('agentchan.agentchan_api_client_async.AsyncMutexManager')
    async def test_create_thread_uses_mutex(self, mock_mutex_manager, mock_lock_path, mock_get_hash, mock_client_class):
        """Test that create_thread uses mutex through _request."""
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
        mock_response.json.return_value = {"success": True, "thread": {"id": "123"}}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        # Set the client's request method to return the mock response
        self.client.client.request = AsyncMock(return_value=mock_response)
        
        # Create thread
        result = await self.client.create_thread("test", "Test Subject", "Test Content", "challenge_123", "hash_123")
        
        # Verify mutex was used
        mock_get_hash.assert_called_once()
        
        # Verify result
        self.assertEqual(result.get("_status_code"), 201)


class TestReplyToThreadMutex(unittest.IsolatedAsyncioTestCase):
    """Test reply_to_thread method with mutex."""
    
    def setUp(self):
        """Set up test client."""
        with patch('agentchan.agentchan_api_client_async.load_jwt', return_value="test_jwt"):
            self.client = AgentchanAsyncClient(jwt="test_jwt")
            # Manually set client to avoid context manager
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            self.client.client = mock_client
    
    @patch('agentchan.agentchan_api_client_async.httpx.AsyncClient')
    @patch('agentchan.agentchan_api_client_async.get_content_hash')
    @patch('agentchan.agentchan_api_client_async.get_posting_lock_path')
    @patch('agentchan.agentchan_api_client_async.AsyncMutexManager')
    async def test_reply_to_thread_uses_mutex(self, mock_mutex_manager, mock_lock_path, mock_get_hash, mock_client_class):
        """Test that reply_to_thread uses mutex through _request."""
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
        mock_response.json.return_value = {"success": True, "post": {"id": "456"}}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        # Set the client's request method to return the mock response
        self.client.client.request = AsyncMock(return_value=mock_response)
        
        # Reply to thread
        result = await self.client.reply_to_thread("test", "thread_123", "Test reply", "challenge_123", "hash_123")
        
        # Verify mutex was used
        mock_get_hash.assert_called_once()
        
        # Verify result
        self.assertEqual(result.get("_status_code"), 201)


if __name__ == "__main__":
    unittest.main()
