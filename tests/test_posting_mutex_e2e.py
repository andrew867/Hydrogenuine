#!/usr/bin/env python3
"""
End-to-end test for posting_mutex.py

Tests real-world usage scenarios to ensure everything works together.
"""
import time
import threading
from pathlib import Path

from hg_core.posting_mutex import (
    posting_lock_with_content,
    get_content_hash,
    get_posting_lock_path,
    _pending_content_hashes,
    _pending_lock,
)


def test_e2e_same_content_blocking():
    """Test that same content blocks duplicate POST requests."""
    print("Testing: Same content blocks duplicate requests...")
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    payload = {"title": "Test Post", "content": "This is a test"}
    endpoint = "/posts"
    content_hash = get_content_hash(payload, endpoint)
    lock_path = get_posting_lock_path("global")
    
    results = []
    
    def simulate_post(post_id, delay=0):
        time.sleep(delay)
        try:
            with posting_lock_with_content(lock_path, content_hash, timeout=0.1, max_wait=1.0):
                results.append(f"post_{post_id}_success")
                time.sleep(0.1)  # Simulate POST request
        except ValueError as e:
            results.append(f"post_{post_id}_blocked: {str(e)[:50]}")
        except Exception as e:
            results.append(f"post_{post_id}_error: {type(e).__name__}")
    
    # Start 3 threads with same content - minimal stagger so they overlap
    threads = []
    for i in range(3):
        t = threading.Thread(target=simulate_post, args=(i, i * 0.02))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Only one should succeed, others should be blocked
    success_count = len([r for r in results if "success" in r])
    blocked_count = len([r for r in results if "blocked" in r])
    
    print(f"  Results: {results}")
    print(f"  Success: {success_count}, Blocked: {blocked_count}")
    
    assert success_count == 1, f"Expected 1 success, got {success_count}"
    assert blocked_count == 2, f"Expected 2 blocked, got {blocked_count}"
    print("  [PASSED]\n")


def test_e2e_different_content_allowed():
    """Test that different content allows concurrent POST requests."""
    print("Testing: Different content allows concurrent requests...")
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    lock_path = get_posting_lock_path("global")
    results = []
    
    def simulate_post(content_text, delay=0):
        time.sleep(delay)
        payload = {"title": "Test", "content": content_text}
        content_hash = get_content_hash(payload, "/posts")
        try:
            with posting_lock_with_content(lock_path, content_hash, timeout=0.1, max_wait=1.0):
                results.append(f"post_{content_text[:10]}_success")
                time.sleep(0.05)  # Simulate POST request
        except Exception as e:
            results.append(f"post_{content_text[:10]}_error: {type(e).__name__}")
    
    # Start 3 threads with different content
    threads = []
    for content in ["Content A", "Content B", "Content C"]:
        t = threading.Thread(target=simulate_post, args=(content,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All should succeed
    success_count = len([r for r in results if "success" in r])
    
    print(f"  Results: {results}")
    print(f"  Success: {success_count}")
    
    assert success_count == 3, f"Expected 3 successes, got {success_count}"
    print("  [PASSED]\n")


def test_e2e_content_hash_consistency():
    """Test that content hash generation is consistent."""
    print("Testing: Content hash consistency...")
    
    payload1 = {"title": "Test", "content": "Hello"}
    payload2 = {"title": "Test", "content": "Hello"}
    payload3 = {"content": "Hello", "title": "Test"}  # Different key order
    
    hash1 = get_content_hash(payload1, "/posts")
    hash2 = get_content_hash(payload2, "/posts")
    hash3 = get_content_hash(payload3, "/posts")
    
    print(f"  Hash1: {hash1[:16]}...")
    print(f"  Hash2: {hash2[:16]}...")
    print(f"  Hash3: {hash3[:16]}...")
    
    assert hash1 == hash2, "Same content should produce same hash"
    assert hash1 == hash3, "Key order shouldn't matter (normalized JSON)"
    print("  [PASSED]\n")


def test_e2e_cleanup_after_exception():
    """Test that cleanup happens even after exception."""
    print("Testing: Cleanup after exception...")
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    payload = {"title": "Test"}
    content_hash = get_content_hash(payload, "/posts")
    lock_path = get_posting_lock_path("global")
    
    try:
        with posting_lock_with_content(lock_path, content_hash, timeout=0.1, max_wait=1.0):
            # Verify hash is in pending set
            with _pending_lock:
                assert content_hash in _pending_content_hashes, "Hash should be in pending set"
            # Raise exception
            raise RuntimeError("Test exception")
    except RuntimeError:
        pass  # Expected
    
    # Hash should be cleaned up
    with _pending_lock:
        assert content_hash not in _pending_content_hashes, "Hash should be cleaned up after exception"
    
    print("  [PASSED]\n")


if __name__ == "__main__":
    print("=" * 60)
    print("End-to-End Tests for posting_mutex.py")
    print("=" * 60 + "\n")
    
    try:
        test_e2e_content_hash_consistency()
        test_e2e_same_content_blocking()
        test_e2e_different_content_allowed()
        test_e2e_cleanup_after_exception()
        
        print("=" * 60)
        print("All end-to-end tests PASSED!")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
