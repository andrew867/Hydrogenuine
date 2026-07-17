"""
In-memory rate limiting for message send and approvals.
"""

import time
from collections import defaultdict
from typing import Tuple

# (identifier -> list of timestamps)
_buckets: dict = defaultdict(list)
# config: max 60 per minute per key
RATE_LIMIT_N = 60
RATE_LIMIT_WINDOW_S = 60


def _prune(bucket: list, window_s: int) -> list:
    now = time.monotonic()
    return [t for t in bucket if now - t < window_s]


def check_rate_limit(identifier: str, n: int = RATE_LIMIT_N, window_s: int = RATE_LIMIT_WINDOW_S) -> Tuple[bool, str]:
    """
    Returns (allowed, message). If not allowed, message explains why.
    """
    bucket = _buckets[identifier]
    bucket = _prune(bucket, window_s)
    if len(bucket) >= n:
        _buckets[identifier] = bucket
        return False, f"Rate limit exceeded: {n} requests per {window_s}s"
    bucket.append(time.monotonic())
    _buckets[identifier] = bucket
    return True, ""


def rate_limit_identifier(request) -> str:
    """Use X-API-Key if present, else client host."""
    key = request.headers.get("X-API-Key") or request.headers.get("Authorization") or ""
    if key:
        return f"key:{key[:32]}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"
