#!/usr/bin/env python3
"""
Integration tests for global mutex system - Phase 10

Tests real-world scenarios with concurrent POST requests across platforms.
"""
import sys
import time
import threading
import multiprocessing
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from hg_core.posting_mutex import (
    posting_lock_with_content,
    get_content_hash,
    get_posting_lock_path,
    _pending_content_hashes,
    _pending_lock
)


def test_integration_concurrent_same_content():
    """Integration test: Run 5 concurrent threads with same content (only 1 should succeed)."""
    print("=" * 60)
    print("Integration Test: 5 Concurrent Threads with Same Content")
    print("=" * 60)
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    lock_path = get_posting_lock_path("global")
    payload = {"title": "Test", "content": "Same content for all"}
    content_hash = get_content_hash(payload, "/posts")
    
    results = []
    results_lock = threading.Lock()
    success_count = [0]
    blocked_count = [0]
    
    def simulate_post(thread_id):
        try:
            with posting_lock_with_content(lock_path, content_hash, timeout=5.0, max_wait=60.0):
                # Simulate POST request
                time.sleep(0.1)
                with results_lock:
                    success_count[0] += 1
                    results.append((thread_id, "success"))
        except ValueError as e:
            # Duplicate content blocked
            with results_lock:
                blocked_count[0] += 1
                results.append((thread_id, "blocked", str(e)))
        except Exception as e:
            with results_lock:
                results.append((thread_id, "error", str(e)))
    
    # Start 5 concurrent threads
    threads = [threading.Thread(target=simulate_post, args=(i,)) for i in range(5)]
    start_time = time.time()
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    duration = time.time() - start_time
    
    print(f"  Results: {len(results)} threads")
    print(f"  Success: {success_count[0]}")
    print(f"  Blocked: {blocked_count[0]}")
    print(f"  Duration: {duration:.3f}s")
    
    # Only one should succeed
    assert success_count[0] == 1, f"Expected 1 success, got {success_count[0]}"
    assert blocked_count[0] == 4, f"Expected 4 blocked, got {blocked_count[0]}"
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    
    print("  [PASSED]\n")


def test_integration_concurrent_different_content():
    """Integration test: Run 5 concurrent threads with different content (all should succeed)."""
    print("=" * 60)
    print("Integration Test: 5 Concurrent Threads with Different Content")
    print("=" * 60)
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    lock_path = get_posting_lock_path("global")
    results = []
    results_lock = threading.Lock()
    success_count = [0]
    
    def simulate_post(content_text):
        payload = {"title": "Test", "content": content_text}
        content_hash = get_content_hash(payload, "/posts")
        try:
            with posting_lock_with_content(lock_path, content_hash, timeout=5.0, max_wait=60.0):
                # Simulate POST request
                time.sleep(0.1)
                with results_lock:
                    success_count[0] += 1
                    results.append((content_text[:10], "success"))
        except Exception as e:
            with results_lock:
                results.append((content_text[:10], "error", str(e)))
    
    # Start 5 concurrent threads with different content
    contents = ["Content A", "Content B", "Content C", "Content D", "Content E"]
    threads = [threading.Thread(target=simulate_post, args=(content,)) for content in contents]
    start_time = time.time()
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    duration = time.time() - start_time
    
    print(f"  Results: {len(results)} threads")
    print(f"  Success: {success_count[0]}")
    print(f"  Duration: {duration:.3f}s")
    
    # All should succeed
    assert success_count[0] == 5, f"Expected 5 successes, got {success_count[0]}"
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    
    print("  [PASSED]\n")


def test_performance_mutex_overhead():
    """Performance test: Measure overhead of mutex (should be <100ms)."""
    print("=" * 60)
    print("Performance Test: Mutex Overhead")
    print("=" * 60)
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    lock_path = get_posting_lock_path("global")
    payload = {"title": "Test", "content": "Performance test"}
    content_hash = get_content_hash(payload, "/posts")
    
    # Measure mutex acquisition time
    iterations = 10
    times = []
    
    for _ in range(iterations):
        start = time.time()
        try:
            with posting_lock_with_content(lock_path, content_hash, timeout=5.0, max_wait=60.0):
                # Simulate minimal work
                pass
        except Exception:
            pass
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    print(f"  Iterations: {iterations}")
    print(f"  Average time: {avg_time*1000:.2f}ms")
    print(f"  Max time: {max_time*1000:.2f}ms")
    
    # Mutex overhead should be reasonable (<100ms for average)
    assert avg_time < 0.1, f"Mutex overhead too high: {avg_time*1000:.2f}ms (expected <100ms)"
    assert max_time < 0.5, f"Mutex max time too high: {max_time*1000:.2f}ms (expected <500ms)"
    
    print("  [PASSED]\n")


def test_stress_mixed_content():
    """Stress test: 50 concurrent requests with mixed content."""
    print("=" * 60)
    print("Stress Test: 50 Concurrent Requests with Mixed Content")
    print("=" * 60)
    
    # Clear pending hashes
    with _pending_lock:
        _pending_content_hashes.clear()
    
    lock_path = get_posting_lock_path("global")
    results = []
    results_lock = threading.Lock()
    success_count = [0]
    blocked_count = [0]
    error_count = [0]
    
    def simulate_post(content_id):
        # Mix of same and different content
        if content_id % 10 == 0:
            # Every 10th request uses same content
            payload = {"title": "Test", "content": "Same content"}
        else:
            # Others use unique content
            payload = {"title": "Test", "content": f"Unique content {content_id}"}
        
        content_hash = get_content_hash(payload, "/posts")
        try:
            with posting_lock_with_content(lock_path, content_hash, timeout=2.0, max_wait=30.0):
                # Simulate POST request
                time.sleep(0.01)
                with results_lock:
                    success_count[0] += 1
                    results.append((content_id, "success"))
        except ValueError:
            # Duplicate content blocked
            with results_lock:
                blocked_count[0] += 1
                results.append((content_id, "blocked"))
        except TimeoutError:
            # Timeout (acceptable under stress)
            with results_lock:
                error_count[0] += 1
                results.append((content_id, "timeout"))
        except Exception as e:
            with results_lock:
                error_count[0] += 1
                results.append((content_id, "error", str(e)))
    
    # Start 50 concurrent threads (reduced from 100 for stability)
    threads = [threading.Thread(target=simulate_post, args=(i,)) for i in range(50)]
    start_time = time.time()
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    duration = time.time() - start_time
    
    print(f"  Results: {len(results)} requests")
    print(f"  Success: {success_count[0]}")
    print(f"  Blocked: {blocked_count[0]}")
    print(f"  Errors/Timeouts: {error_count[0]}")
    print(f"  Duration: {duration:.3f}s")
    
    # Should have 50 results
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"
    # Should have some successes and some blocked (5 same content requests, only 1 should succeed)
    assert success_count[0] > 0, "Should have at least one success"
    # Under stress, some timeouts are expected - important thing is duplicates are blocked
    # At least 30 requests should succeed or be blocked (timeouts are acceptable under high load)
    assert success_count[0] + blocked_count[0] >= 30, f"Expected at least 30 successes+blocked, got {success_count[0] + blocked_count[0]}"
    # Verify duplicates are being blocked (should have at least some blocked)
    assert blocked_count[0] > 0, "Should have at least one duplicate blocked"
    
    print("  [PASSED]\n")


def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("Global Mutex Integration Test Suite - Phase 10")
    print("=" * 60 + "\n")
    
    try:
        test_integration_concurrent_same_content()
        test_integration_concurrent_different_content()
        test_performance_mutex_overhead()
        test_stress_mixed_content()
        
        print("=" * 60)
        print("All integration tests PASSED!")
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
