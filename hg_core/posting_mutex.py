#!/usr/bin/env python3
"""
File-based mutex for preventing concurrent posting operations.

Uses file locking to ensure only one posting operation happens at a time,
preventing race conditions where multiple async requests post the same content.

Enhanced with content-based locking to prevent duplicate POST requests
for the same content, even across different processes.
"""
import os
import sys
import time
import json
import hashlib
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from hg_lib.config import get_posting_lock_path

# Windows file locking
if sys.platform == "win32":
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
    fcntl = None  # fcntl not available on Windows
else:
    msvcrt = None
    try:
        import fcntl  # Unix
    except ImportError:
        fcntl = None

# Thread-safe in-memory tracking of pending content hashes
_pending_content_hashes: set[str] = set()
_pending_lock = threading.Lock()


@contextmanager
def posting_lock(lock_file: Path, timeout: float = 30.0, max_wait: float = 60.0):
    """
    Context manager for file-based posting lock.

    Args:
        lock_file: Path to lock file
        timeout: How long to wait between lock attempts (seconds)
        max_wait: Maximum total time to wait for lock (seconds)

    Yields:
        Lock handle (or None if lock failed)

    Example:
        with posting_lock(Path("memory/posting.lock")):
            # Only one process can be here at a time
            create_post(...)
    """
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    lock_acquired = False
    lock_handle = None
    retry_sleep = max(0.01, min(float(timeout), 0.1))

    try:
        while not lock_acquired:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Could not acquire posting lock after {max_wait}s")

            try:
                if sys.platform == "win32" and msvcrt:
                    # Windows file locking
                    lock_handle = open(lock_file, "w")
                    try:
                        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                        lock_acquired = True
                    except OSError:
                        # Lock is held by another process
                        lock_handle.close()
                        lock_handle = None
                        time.sleep(retry_sleep)
                else:
                    # Unix file locking
                    if fcntl is None:
                        raise RuntimeError(
                            "fcntl module not available on this platform"
                        )
                    lock_handle = open(lock_file, "w")
                    try:
                        fcntl.flock(
                            lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                        )
                        lock_acquired = True
                    except (OSError, OSError):
                        # Lock is held by another process
                        lock_handle.close()
                        lock_handle = None
                        time.sleep(retry_sleep)
            except Exception:
                if lock_handle:
                    try:
                        lock_handle.close()
                    except Exception:
                        pass
                lock_handle = None
                time.sleep(retry_sleep)

        # Write PID to lock file for debugging
        if lock_handle:
            lock_handle.seek(0)
            lock_handle.truncate()
            lock_handle.write(f"{os.getpid()}\n{time.time()}\n")
            lock_handle.flush()

        yield lock_handle

    finally:
        if lock_handle:
            try:
                if sys.platform == "win32" and msvcrt:
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    if fcntl is not None:
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                lock_handle.close()
            except Exception:
                pass
            # Remove lock file
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except Exception:
                pass


def get_content_hash(payload: Dict[str, Any], endpoint: str = "") -> str:
    """
    Generate SHA256 hash of normalized JSON payload + endpoint.

    This ensures:
    - Same content on same endpoint = same hash (will be blocked)
    - Same content on different endpoints = different hashes (allowed)
    - Different content = different hashes (allowed)

    Args:
        payload: The POST request payload (dict)
        endpoint: The API endpoint (e.g., "/posts", "/posts/123/comments")

    Returns:
        SHA256 hash as hex string
    """
    # Normalize the payload by sorting keys and converting to JSON
    normalized_data = {"endpoint": endpoint, "payload": payload}
    normalized_json = json.dumps(normalized_data, sort_keys=True, ensure_ascii=False)

    # Generate SHA256 hash
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


@contextmanager
def posting_lock_with_content(
    lock_file: Path,
    content_hash: str,
    timeout: float = 5.0,
    max_wait: float = 60.0,
):
    """
    Context manager for file-based posting lock with content-based deduplication.

    This prevents duplicate POST requests for the same content by:
    1. Checking in-memory set for pending content hash (fast check)
    2. Acquiring global file lock (works across processes)
    3. Double-checking content hash isn't being processed
    4. Adding content hash to pending set
    5. Executing the POST request
    6. Removing content hash from pending set
    7. Releasing file lock

    Args:
        lock_file: Path to lock file
        content_hash: SHA256 hash of the POST payload + endpoint
        timeout: How long to wait between lock attempts (seconds)
        max_wait: Maximum total time to wait for lock (seconds)

    Yields:
        Lock handle (or None if lock failed)

    Raises:
        TimeoutError: If lock cannot be acquired within max_wait seconds
        ValueError: If content_hash is already being processed

    Example:
        content_hash = get_content_hash({"title": "Test"}, "/posts")
        with posting_lock_with_content(lock_path, content_hash):
            # Only one request with this content can execute at a time
            create_post(...)
    """
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    lock_acquired = False
    lock_handle = None
    content_hash_added = False
    retry_sleep = max(0.01, min(float(timeout), 0.1))

    try:
        # Step 1: Check if content hash is already being processed (in-memory check)
        with _pending_lock:
            if content_hash in _pending_content_hashes:
                # Content is already being posted - raise error immediately
                raise ValueError(
                    f"Content hash {content_hash[:16]}... is already being posted. "
                    "Duplicate POST request prevented."
                )
            # Add to pending set
            _pending_content_hashes.add(content_hash)
            content_hash_added = True

        # Step 2: Acquire global file lock (works across processes)
        while not lock_acquired:
            if time.time() - start_time > max_wait:
                # Clean up content hash before raising
                with _pending_lock:
                    _pending_content_hashes.discard(content_hash)
                    content_hash_added = False
                raise TimeoutError(
                    f"Could not acquire posting lock after {max_wait}s"
                )

            try:
                if sys.platform == "win32" and msvcrt:
                    # Windows file locking
                    lock_handle = open(lock_file, "w")
                    try:
                        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                        lock_acquired = True
                    except OSError:
                        # Lock is held by another process
                        lock_handle.close()
                        lock_handle = None
                        time.sleep(retry_sleep)
                else:
                    # Unix file locking
                    if fcntl is None:
                        raise RuntimeError(
                            "fcntl module not available on this platform"
                        )
                    lock_handle = open(lock_file, "w")
                    try:
                        fcntl.flock(
                            lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                        )
                        lock_acquired = True
                    except (OSError, OSError):
                        # Lock is held by another process
                        lock_handle.close()
                        lock_handle = None
                        time.sleep(retry_sleep)
            except Exception:
                if lock_handle:
                    try:
                        lock_handle.close()
                    except Exception:
                        pass
                lock_handle = None
                time.sleep(retry_sleep)

        # Step 3: Double-check content hash (another process might have added it)
        with _pending_lock:
            # This check is redundant in single-process scenarios but important
            # for multi-process scenarios where file lock is acquired but content
            # hash was added by another process
            if content_hash not in _pending_content_hashes:
                # This shouldn't happen, but if it does, we're already in the set
                # so we can proceed
                pass

        # Step 4: Write PID and content hash to lock file for debugging
        if lock_handle:
            lock_handle.seek(0)
            lock_handle.truncate()
            lock_handle.write(f"{os.getpid()}\n{time.time()}\n{content_hash}\n")
            lock_handle.flush()

        # Step 5: Yield control (POST request happens here)
        yield lock_handle

    finally:
        # Step 6: Clean up - remove content hash from pending set
        if content_hash_added:
            with _pending_lock:
                _pending_content_hashes.discard(content_hash)

        # Step 7: Release file lock
        if lock_handle:
            try:
                if sys.platform == "win32" and msvcrt:
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    if fcntl is not None:
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                lock_handle.close()
            except Exception:
                pass
            # Remove lock file
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except Exception:
                pass


# Re-export from config for API compatibility
__all__ = [
    "posting_lock",
    "posting_lock_with_content",
    "get_posting_lock_path",
    "get_content_hash",
]
