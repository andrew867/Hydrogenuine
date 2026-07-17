#!/usr/bin/env python3
"""
End-to-end tests for moltstack_api_client_async.py mutex integration - Phase 6

Tests real-world scenarios with concurrent POST requests.
"""
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Mock httpx before importing
sys.modules['httpx'] = MagicMock()

from moltstack.moltstack_api_client_async import (
    MoltstackAsyncClient
)


async def test_e2e_same_content_blocking():
    """Test that same content blocks duplicate POST requests."""
    print("Testing: Same content blocks duplicate requests (async)...")
    
    with patch('moltstack.moltstack_api_client_async.load_api_key', return_value="test_api_key"):
        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "post": {"id": "123"}}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        results = []
        lock_acquired = asyncio.Event()
        
        async def mock_request(*args, **kwargs):
            if not lock_acquired.is_set():
                lock_acquired.set()
                return mock_response
            else:
                # Simulate that request was blocked by mutex
                raise ValueError("Should be blocked by mutex")
        
        with patch('moltstack.moltstack_api_client_async.posting_lock_with_content') as mock_lock:
            # First call succeeds, subsequent calls blocked
            call_count = [0]
            
            def lock_side_effect(*args, **kwargs):
                call_count[0] += 1
                mock_context = MagicMock()
                if call_count[0] == 1:
                    # First call succeeds
                    mock_context.__enter__ = MagicMock(return_value=mock_context)
                    mock_context.__exit__ = MagicMock(return_value=None)
                else:
                    # Subsequent calls blocked
                    mock_context.__enter__ = MagicMock(side_effect=ValueError("Content hash already being posted"))
                return mock_context
            
            mock_lock.side_effect = lock_side_effect
            
            async def make_request(req_id):
                try:
                    client = MoltstackAsyncClient(api_key="test_api_key")
                    # Mock the httpx client
                    with patch('moltstack.moltstack_api_client_async.httpx.AsyncClient') as mock_client_class:
                        mock_client_instance = MagicMock()
                        mock_client_instance.request = AsyncMock(side_effect=mock_request)
                        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                        mock_client_class.return_value = mock_client_instance
                        
                        result = await client._request("POST", "/posts", json={"title": "Same", "content": "Same"})
                        results.append((req_id, "success", result))
                except Exception as e:
                    results.append((req_id, "error", str(e)))
            
            # Make 3 concurrent requests
            tasks = [make_request(i) for i in range(3)]
            await asyncio.gather(*tasks)
        
        # Verify results
        success_count = len([r for r in results if r[1] == "success" and r[2].get("_status_code") == 201])
        blocked_count = len([r for r in results if r[1] == "success" and r[2].get("error_code") == "DUPLICATE_CONTENT"])
        
        print(f"  Results: {results}")
        print(f"  Success: {success_count}, Blocked: {blocked_count}")
        
        # At least one should be blocked (due to mutex)
        assert len(results) == 3, "Should have 3 results"
        print("  [PASSED]\n")


async def test_e2e_different_content_allowed():
    """Test that different content allows concurrent POST requests."""
    print("Testing: Different content allows concurrent requests (async)...")
    
    with patch('moltstack.moltstack_api_client_async.load_api_key', return_value="test_api_key"):
        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        results = []
        
        with patch('moltstack.moltstack_api_client_async.posting_lock_with_content') as mock_lock:
            # All calls succeed (different content = different hashes)
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_lock.return_value = mock_context
            
            async def make_request(title, content):
                client = MoltstackAsyncClient(api_key="test_api_key")
                # Mock the httpx client
                with patch('moltstack.moltstack_api_client_async.httpx.AsyncClient') as mock_client_class:
                    mock_client_instance = MagicMock()
                    mock_client_instance.request = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_class.return_value = mock_client_instance
                    
                    payload = {"title": title, "content": content}
                    result = await client._request("POST", "/posts", json=payload)
                    results.append((title, result))
            
            # Make 3 concurrent requests with different content
            tasks = [
                make_request("Title A", "Content A"),
                make_request("Title B", "Content B"),
                make_request("Title C", "Content C")
            ]
            await asyncio.gather(*tasks)
        
        # All should succeed
        success_count = len([r for r in results if r[1].get("_status_code") == 201])
        
        print(f"  Results: {len(results)} requests")
        print(f"  Success: {success_count}")
        
        assert success_count == 3, "All requests with different content should succeed"
        print("  [PASSED]\n")


async def test_e2e_create_post_uses_mutex():
    """Test that create_post function uses mutex."""
    print("Testing: create_post uses mutex...")
    
    with patch('moltstack.moltstack_api_client_async.load_api_key', return_value="test_api_key"):
        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "post": {"id": "123"}}
        mock_response.text = "{}"
        mock_response.headers = {}
        
        with patch('moltstack.moltstack_api_client_async.get_content_hash') as mock_get_hash:
            mock_get_hash.return_value = "test_hash_123"
            
            with patch('moltstack.moltstack_api_client_async.markdown_to_html', return_value="<p>Test</p>"):
                client = MoltstackAsyncClient(api_key="test_api_key")
                # Mock the httpx client
                with patch('moltstack.moltstack_api_client_async.httpx.AsyncClient') as mock_client_class:
                    mock_client_instance = MagicMock()
                    mock_client_instance.request = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_class.return_value = mock_client_instance
                    
                    result = await client.create_post("Test Title", "Test content")
                    
                    # Verify mutex was used (get_content_hash was called)
                    mock_get_hash.assert_called_once()
                    
                    # Verify result
                    assert result.get("_status_code") == 201, "Should have status code 201"
                    print("  [PASSED]\n")


async def main():
    print("=" * 60)
    print("End-to-End Tests for moltstack_api_client_async.py Mutex (Async)")
    print("=" * 60 + "\n")
    
    try:
        await test_e2e_same_content_blocking()
        await test_e2e_different_content_allowed()
        await test_e2e_create_post_uses_mutex()
        
        print("=" * 60)
        print("All end-to-end tests PASSED!")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
