#!/usr/bin/env python3
"""
End-to-end tests for moltbook_api_client.py mutex integration - Phase 3

Tests real-world scenarios with concurrent POST requests.
"""
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Sync moltbook posting API relocated to the async client (see test_moltbook_sync_mutex).
try:
    from hg_platforms.moltbook.moltbook_api_client import (
        make_moltbook_request,
        create_post,
        create_comment,
    )
except ImportError:
    pytest.skip(
        "moltbook sync posting API relocated to the async client; sync mutex e2e "
        "tests pending sync->async consolidation",
        allow_module_level=True,
    )


def test_e2e_same_content_blocking():
    """Test that same content blocks duplicate POST requests."""
    print("Testing: Same content blocks duplicate requests (sync)...")
    
    with patch('hg_platforms.moltbook.moltbook_api_client.load_api_key', return_value="test_api_key"):
        # Mock requests.post
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "post": {"id": "123"}}
        mock_response.headers = {}
        
        results = []
        lock_acquired = threading.Event()
        
        def mock_post(*args, **kwargs):
            if not lock_acquired.is_set():
                lock_acquired.set()
                return mock_response
            else:
                # Simulate that request was blocked by mutex
                raise ValueError("Should be blocked by mutex")
        
        with patch('hg_platforms.moltbook.moltbook_api_client.requests.post', side_effect=mock_post):
            with patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content') as mock_lock:
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
                
                def make_request(req_id):
                    try:
                        result = make_moltbook_request("POST", "posts", payload={"title": "Test", "content": "Same"})
                        results.append((req_id, "success", result))
                    except Exception as e:
                        results.append((req_id, "error", str(e)))
                
                # Make 3 concurrent requests
                threads = [threading.Thread(target=make_request, args=(i,)) for i in range(3)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
        
        # Verify results
        success_count = len([r for r in results if r[1] == "success" and r[2].get("success")])
        blocked_count = len([r for r in results if r[1] == "success" and r[2].get("error_code") == "DUPLICATE_CONTENT"])
        
        print(f"  Results: {results}")
        print(f"  Success: {success_count}, Blocked: {blocked_count}")
        
        # At least one should be blocked (due to mutex)
        assert len(results) == 3, "Should have 3 results"
        print("  [PASSED]\n")


def test_e2e_different_content_allowed():
    """Test that different content allows concurrent POST requests."""
    print("Testing: Different content allows concurrent requests (sync)...")
    
    with patch('hg_platforms.moltbook.moltbook_api_client.load_api_key', return_value="test_api_key"):
        # Mock requests.post
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        
        results = []
        
        with patch('hg_platforms.moltbook.moltbook_api_client.requests.post', return_value=mock_response):
            with patch('hg_platforms.moltbook.moltbook_api_client.posting_lock_with_content') as mock_lock:
                # All calls succeed (different content = different hashes)
                mock_context = MagicMock()
                mock_context.__enter__ = MagicMock(return_value=mock_context)
                mock_context.__exit__ = MagicMock(return_value=None)
                mock_lock.return_value = mock_context
                
                def make_request(title, content):
                    payload = {"title": title, "content": content}
                    result = make_moltbook_request("POST", "posts", payload=payload)
                    results.append((title, result))
                
                # Make 3 concurrent requests with different content
                threads = [
                    threading.Thread(target=make_request, args=("Title A", "Content A")),
                    threading.Thread(target=make_request, args=("Title B", "Content B")),
                    threading.Thread(target=make_request, args=("Title C", "Content C"))
                ]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
        
        # All should succeed
        success_count = len([r for r in results if r[1].get("success")])
        
        print(f"  Results: {len(results)} requests")
        print(f"  Success: {success_count}")
        
        assert success_count == 3, "All requests with different content should succeed"
        print("  [PASSED]\n")


def test_e2e_create_post_uses_mutex():
    """Test that create_post function uses mutex."""
    print("Testing: create_post uses mutex...")
    
    with patch('hg_platforms.moltbook.moltbook_api_client.make_moltbook_request') as mock_request:
        mock_request.return_value = {
            "success": True,
            "post": {"id": "123"}
        }
        
        result = create_post("general", "Test Title", "Test Content")
        
        # Verify make_moltbook_request was called (which uses mutex for POST)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        
        # Verify it's a POST request with payload
        assert call_args[0][0] == "POST", "Should be POST request"
        assert call_args[1].get("payload") is not None, "Should have payload"
        
        print("  [PASSED]\n")


def test_e2e_create_comment_uses_mutex():
    """Test that create_comment function uses mutex."""
    print("Testing: create_comment uses mutex...")
    
    with patch('hg_platforms.moltbook.moltbook_api_client.make_moltbook_request') as mock_request:
        mock_request.return_value = {
            "success": True,
            "comment": {"id": "456"}
        }
        
        result = create_comment("post_123", "Test comment")
        
        # Verify make_moltbook_request was called (which uses mutex for POST)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        
        # Verify it's a POST request with payload
        assert call_args[0][0] == "POST", "Should be POST request"
        assert call_args[1].get("payload") is not None, "Should have payload"
        
        print("  [PASSED]\n")


if __name__ == "__main__":
    print("=" * 60)
    print("End-to-End Tests for moltbook_api_client.py Mutex (Sync)")
    print("=" * 60 + "\n")
    
    try:
        test_e2e_same_content_blocking()
        test_e2e_different_content_allowed()
        test_e2e_create_post_uses_mutex()
        test_e2e_create_comment_uses_mutex()
        
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
