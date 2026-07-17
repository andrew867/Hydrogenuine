"""
Control Surface Pack 12: Cache layer for fusion decision cards and why-blocked explanations.
Cache invalidation driven by ledger events / pinset changes; TTL and max size.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

# TTL seconds for fusion card and explain_block entries
CACHE_TTL_SECONDS = 60
# Max entries per cache (fusion, explain)
CACHE_MAX_ENTRIES = 1000

_lock = threading.Lock()
_fusion_cache: Dict[str, tuple[float, Any]] = {}
_explain_cache: Dict[str, tuple[float, Any]] = {}
_hits = 0
_misses = 0


def _cache_key(workspace_id: str, suffix: str) -> str:
    return f"{workspace_id}:{suffix}"


def _evict_expired(cache: Dict[str, tuple[float, Any]], max_entries: int) -> None:
    now = time.monotonic()
    expired = [k for k, (ts, _) in cache.items() if now - ts > CACHE_TTL_SECONDS]
    for k in expired:
        del cache[k]
    while len(cache) > max_entries:
        oldest = min(cache.keys(), key=lambda k: cache[k][0])
        del cache[oldest]


def get_fusion_card(workspace_id: str, card_id: str) -> Optional[Any]:
    """Return cached fusion card detail or None."""
    global _hits, _misses
    with _lock:
        _evict_expired(_fusion_cache, CACHE_MAX_ENTRIES)
        key = _cache_key(workspace_id, f"card:{card_id}")
        if key in _fusion_cache:
            _hits += 1
            ts, val = _fusion_cache[key]
            if time.monotonic() - ts <= CACHE_TTL_SECONDS:
                return val
            del _fusion_cache[key]
        _misses += 1
        return None


def set_fusion_card(workspace_id: str, card_id: str, value: Any) -> None:
    """Store fusion card detail in cache."""
    with _lock:
        _evict_expired(_fusion_cache, CACHE_MAX_ENTRIES)
        _fusion_cache[_cache_key(workspace_id, f"card:{card_id}")] = (time.monotonic(), value)


def get_explain(workspace_id: str, ref_id: str) -> Optional[Any]:
    """Return cached explain_block result or None."""
    global _hits, _misses
    with _lock:
        _evict_expired(_explain_cache, CACHE_MAX_ENTRIES)
        key = _cache_key(workspace_id, f"explain:{ref_id}")
        if key in _explain_cache:
            _hits += 1
            ts, val = _explain_cache[key]
            if time.monotonic() - ts <= CACHE_TTL_SECONDS:
                return val
            del _explain_cache[key]
        _misses += 1
        return None


def set_explain(workspace_id: str, ref_id: str, value: Any) -> None:
    """Store explain_block result in cache."""
    with _lock:
        _evict_expired(_explain_cache, CACHE_MAX_ENTRIES)
        _explain_cache[_cache_key(workspace_id, f"explain:{ref_id}")] = (time.monotonic(), value)


def invalidate_all() -> None:
    """Invalidate all cache entries (e.g. on ledger/pinset change)."""
    with _lock:
        _fusion_cache.clear()
        _explain_cache.clear()


def get_or_set_fusion(workspace_id: str, card_id: str, loader: Any) -> Any:
    """Return cached fusion card or call loader() and cache result. loader is a callable returning card dict or None."""
    val = get_fusion_card(workspace_id, card_id)
    if val is not None:
        return val
    val = loader() if callable(loader) else loader
    if val is not None:
        set_fusion_card(workspace_id, card_id, val)
    return val


def get_or_set_explain(workspace_id: str, ref_id: str, loader: Any) -> Any:
    """Return cached explain result or call loader() and cache. loader is a callable returning explain dict or None."""
    val = get_explain(workspace_id, ref_id)
    if val is not None:
        return val
    val = loader() if callable(loader) else loader
    if val is not None:
        set_explain(workspace_id, ref_id, val)
    return val


def get_cache_stats() -> Dict[str, Any]:
    """Return hit count, miss count, and sizes for admin API."""
    with _lock:
        total = _hits + _misses
        hit_rate = _hits / total if total else 0.0
        return {
            "fusion_entries": len(_fusion_cache),
            "explain_entries": len(_explain_cache),
            "hits": _hits,
            "misses": _misses,
            "hit_rate": round(hit_rate, 4),
        }
