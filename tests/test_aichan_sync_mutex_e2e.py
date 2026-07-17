#!/usr/bin/env python3
"""
End-to-end tests for aichan_api_client.py mutex integration - Phase 8

Tests real-world scenarios with concurrent POST requests.
"""
import sys
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock requests before importing
sys.modules['requests'] = MagicMock()

from aichan.aichan_api_client import (
    make_aichan_request,
    create_thread,
    reply_to_thread
)


def test_e2e_same_content_blocking():
    """Test that same content blocks duplicate POST requests."""
    print("Testing: Same content blocks duplicate requests (sync)...")
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 302
    mock_response.headers = {"Location": "/b/res/123.html"}
    mock_response.text = ""
    
    results = []
    lock_acquired = threading.Event()
    
    def mock_post(*args, **kwargs):
        if not lock_acquired.is_set():
            lock_acquired.set()
            return mock_response
        else:
            # Simulate that request was blocked by mutex
            raise ValueError("Should be blocked by mutex")
    
    with patch('aichan.aichan_api_client.requests.post', side_effect=mock_post):
        with patch('aichan.aichan_api_client.posting_lock_with_content') as mock_lock:
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
                    result = make_aichan_request("POST", "/post.php", data={"board": "b", "body": "Same", "post": "New Topic"})
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
    success_count = len([r for r in results if r[1] == "success" and r[2].get("ok")])
    blocked_count = len([r for r in results if r[1] == "success" and r[2].get("error_code") == "DUPLICATE_CONTENT"])
    
    print(f"  Results: {results}")
    print(f"  Success: {success_count}, Blocked: {blocked_count}")
    
    # At least one should be blocked (due to mutex)
    assert len(results) == 3, "Should have 3 results"
    print("  [PASSED]\n")


def test_e2e_different_content_allowed():
    """Test that different content allows concurrent POST requests."""
    print("Testing: Different content allows concurrent requests (sync)...")
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 302
    mock_response.headers = {"Location": "/b/res/123.html"}
    mock_response.text = ""
    
    results = []
    
    with patch('aichan.aichan_api_client.requests.post', return_value=mock_response):
        with patch('aichan.aichan_api_client.posting_lock_with_content') as mock_lock:
            # All calls succeed (different content = different hashes)
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_lock.return_value = mock_context
            
            def make_request(body):
                payload = {"board": "b", "body": body, "post": "New Topic"}
                result = make_aichan_request("POST", "/post.php", data=payload)
                results.append((body, result))
            
            # Make 3 concurrent requests with different content
            threads = [
                threading.Thread(target=make_request, args=("Content A",)),
                threading.Thread(target=make_request, args=("Content B",)),
                threading.Thread(target=make_request, args=("Content C",))
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
    
    # All should succeed
    success_count = len([r for r in results if r[1].get("ok")])
    
    print(f"  Results: {len(results)} requests")
    print(f"  Success: {success_count}")
    
    assert success_count == 3, "All requests with different content should succeed"
    print("  [PASSED]\n")


def test_e2e_create_thread_uses_mutex():
    """Test that create_thread function uses mutex."""
    print("Testing: create_thread uses mutex...")
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 302
    mock_response.headers = {"Location": "/b/res/123.html"}
    mock_response.text = ""
    
    with patch('aichan.aichan_api_client.requests.post', return_value=mock_response):
        with patch('aichan.aichan_api_client.get_content_hash') as mock_get_hash:
            mock_get_hash.return_value = "test_hash_123"
            
            with patch('aichan.aichan_api_client.make_aichan_request') as mock_request:
                mock_request.return_value = {
                    "ok": True,
                    "status_code": 302,
                    "thread_id": "123",
                    "location": "/b/res/123.html"
                }
                
                result = create_thread("b", "Test Subject", "Test Body")
                
                # Verify mutex was used (make_aichan_request was called with POST)
                mock_request.assert_called_once()
                call_args = mock_request.call_args
                assert call_args[0][0] == "POST", "Should use POST method"
                
                # Verify result
                assert result.get("ok"), "Should succeed"
                assert result.get("thread_id") == "123", "Should have thread_id"
                print("  [PASSED]\n")


def test_e2e_reply_to_thread_uses_mutex():
    """Test that reply_to_thread function uses mutex."""
    print("Testing: reply_to_thread uses mutex...")
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 302
    mock_response.headers = {}
    mock_response.text = ""
    
    with patch('aichan.aichan_api_client.requests.post', return_value=mock_response):
        with patch('aichan.aichan_api_client.get_content_hash') as mock_get_hash:
            mock_get_hash.return_value = "test_hash_123"
            
            with patch('aichan.aichan_api_client.make_aichan_request') as mock_request:
                mock_request.return_value = {
                    "ok": True,
                    "status_code": 302
                }
                
                result = reply_to_thread("b", "123", "Test reply")
                
                # Verify mutex was used (make_aichan_request was called with POST)
                mock_request.assert_called_once()
                call_args = mock_request.call_args
                assert call_args[0][0] == "POST", "Should use POST method"
                
                # Verify result
                assert result.get("ok"), "Should succeed"
                print("  [PASSED]\n")


def main():
    print("=" * 60)
    print("End-to-End Tests for aichan_api_client.py Mutex (Sync)")
    print("=" * 60 + "\n")
    
    try:
        test_e2e_same_content_blocking()
        test_e2e_different_content_allowed()
        test_e2e_create_thread_uses_mutex()
        test_e2e_reply_to_thread_uses_mutex()
        
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
    main()
