#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance optimization for memory engine.

Provides caching, connection pooling, and performance monitoring.
"""

import time
import hashlib
import functools
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import OrderedDict
import threading

from hg_memory.config import get_config


class QueryCache:
    """LRU cache for query results"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize query cache.

        Args:
            max_size: Maximum number of cached queries
            ttl_seconds: Time-to-live for cached results (seconds)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()

    def _make_key(self, query: str, language: Optional[str], agent_id: Optional[str]) -> str:
        """Create cache key from query parameters"""
        key_str = f"{query}:{language}:{agent_id}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, query: str, language: Optional[str] = None, agent_id: Optional[str] = None) -> Optional[Any]:
        """
        Get cached result.

        Args:
            query: Search query
            language: Optional language code
            agent_id: Optional agent ID

        Returns:
            Cached result or None if not found/expired
        """
        with self.lock:
            key = self._make_key(query, language, agent_id)

            if key not in self.cache:
                return None

            result, timestamp = self.cache[key]

            # Check if expired
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return result

    def set(self, query: str, result: Any, language: Optional[str] = None, agent_id: Optional[str] = None):
        """
        Cache result.

        Args:
            query: Search query
            result: Result to cache
            language: Optional language code
            agent_id: Optional agent ID
        """
        with self.lock:
            key = self._make_key(query, language, agent_id)

            # Remove if exists
            if key in self.cache:
                del self.cache[key]

            # Add to end
            self.cache[key] = (result, time.time())

            # Evict oldest if over limit
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def clear(self):
        """Clear all cached results"""
        with self.lock:
            self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }


# Global query cache instance
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance"""
    global _query_cache
    if _query_cache is None:
        config = get_config()
        indexing_config = config.get_indexing_config()
        # Use config if available, otherwise defaults
        max_size = indexing_config.get("cache_max_size", 100)
        ttl = indexing_config.get("cache_ttl_seconds", 300)
        _query_cache = QueryCache(max_size=max_size, ttl_seconds=ttl)
    return _query_cache


def cached_query(ttl_seconds: int = 300):
    """
    Decorator for caching query results.

    Args:
        ttl_seconds: Time-to-live for cached results
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract query parameters
            query = kwargs.get('query') or (args[1] if len(args) > 1 else None)
            language = kwargs.get('language')
            agent_id = kwargs.get('agent_id')

            cache = get_query_cache()

            # Try cache first
            cached_result = cache.get(query, language, agent_id)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            if query:
                cache.set(query, result, language, agent_id)

            return result

        return wrapper
    return decorator


class PerformanceMonitor:
    """Monitor performance metrics"""

    def __init__(self):
        """Initialize performance monitor"""
        self.metrics: Dict[str, list] = {}
        self.lock = threading.Lock()

    def record_operation(self, operation: str, duration_ms: float, success: bool = True):
        """
        Record operation performance.

        Args:
            operation: Operation name (e.g., "search", "index")
            duration_ms: Operation duration in milliseconds
            success: Whether operation was successful
        """
        with self.lock:
            if operation not in self.metrics:
                self.metrics[operation] = []

            self.metrics[operation].append({
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })

            # Keep only last 1000 entries per operation
            if len(self.metrics[operation]) > 1000:
                self.metrics[operation] = self.metrics[operation][-1000:]

    def get_stats(self, operation: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance statistics for operation.

        Args:
            operation: Operation name
            hours: Number of hours to look back

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            if operation not in self.metrics:
                return {
                    "count": 0,
                    "avg_duration_ms": 0,
                    "p50_duration_ms": 0,
                    "p95_duration_ms": 0,
                    "p99_duration_ms": 0,
                    "success_rate": 0
                }

            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent = [
                m for m in self.metrics[operation]
                if datetime.fromisoformat(m["timestamp"]) >= cutoff_time
            ]

            if not recent:
                return {
                    "count": 0,
                    "avg_duration_ms": 0,
                    "p50_duration_ms": 0,
                    "p95_duration_ms": 0,
                    "p99_duration_ms": 0,
                    "success_rate": 0
                }

            durations = sorted([m["duration_ms"] for m in recent])
            successes = [m["success"] for m in recent]

            return {
                "count": len(recent),
                "avg_duration_ms": sum(durations) / len(durations),
                "p50_duration_ms": durations[len(durations) // 2],
                "p95_duration_ms": durations[int(len(durations) * 0.95)],
                "p99_duration_ms": durations[int(len(durations) * 0.99)],
                "success_rate": sum(successes) / len(successes) if successes else 0
            }


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def monitor_performance(operation: str):
    """
    Decorator for monitoring operation performance.

    Args:
        operation: Operation name
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                monitor.record_operation(operation, duration_ms, success)

        return wrapper
    return decorator
