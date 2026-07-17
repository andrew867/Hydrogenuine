"""Rate limiter and TTL cache for search tools. Phase 7."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class RateLimiter:
    """Simple rate limiter: max N requests per window_seconds."""

    def __init__(self, requests_per_minute: int = 60, window_s: float = 60.0) -> None:
        self._rpm = max(1, requests_per_minute)
        self._window_s = max(0.1, window_s)
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def check(self) -> bool:
        """Return True if request is allowed, False if rate exceeded."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_s
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            if len(self._timestamps) >= self._rpm:
                return False
            self._timestamps.append(now)
            return True


class TTLCache:
    """In-memory cache with TTL (seconds). Thread-safe."""

    def __init__(self, ttl_seconds: float = 3600.0, max_entries: int = 1000) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires = entry
            if time.monotonic() > expires:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max and key not in self._store:
                # Evict oldest
                now = time.monotonic()
                oldest = min(self._store.items(), key=lambda e: e[1][1])
                del self._store[oldest[0]]
            expires = time.monotonic() + self._ttl
            self._store[key] = (value, expires)
