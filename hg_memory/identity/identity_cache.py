#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caching layer for identity graph queries.

Provides query result caching and connection pooling.
"""

import time
import threading
from typing import Dict, Optional, List, Any
from functools import wraps
import hashlib
import json

from .identity_graph_db import IdentityGraphDatabase


class IdentityCache:
    """Cache for identity graph queries"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
            max_size: Maximum number of cache entries
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._access_times: Dict[str, float] = {}
    
    def _make_key(self, func_name: str, *args, **kwargs) -> str:
        """Create cache key from function name and arguments"""
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if time.time() > entry['expires_at']:
                # Expired
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                return None
            
            # Update access time
            self._access_times[key] = time.time()
            return entry['value']
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Evict if at max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = {
                'value': value,
                'expires_at': time.time() + self.ttl_seconds,
                'created_at': time.time()
            }
            self._access_times[key] = time.time()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._access_times:
            # No access times, evict oldest
            if self._cache:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['created_at'])
                del self._cache[oldest_key]
            return
        
        # Evict least recently accessed
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[lru_key]
        del self._access_times[lru_key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (simple substring match)
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]


def cached(ttl_seconds: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time-to-live for cache entries
    """
    def decorator(func):
        cache = IdentityCache(ttl_seconds=ttl_seconds)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if first arg is self (instance method)
            if args and hasattr(args[0], '__class__'):
                # Instance method - include instance ID in key
                instance_id = id(args[0])
                cache_key = cache._make_key(func.__name__, instance_id, *args[1:], **kwargs)
            else:
                cache_key = cache._make_key(func.__name__, *args, **kwargs)
            
            # Try cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result)
            
            return result
        
        wrapper.cache = cache
        return wrapper
    return decorator
