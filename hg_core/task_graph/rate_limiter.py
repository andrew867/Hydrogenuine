"""Per-tool token bucket rate limiter for the tool contract layer."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .tool_validator import ToolContractError


class TokenBucket:
    """Simple token bucket: refill at rate per second, capacity burst, one request = one token."""

    def __init__(self, requests_per_minute: int, burst: Optional[int] = None) -> None:
        self.refill_per_second = requests_per_minute / 60.0
        self.capacity = burst if burst is not None else max(1, requests_per_minute)
        self.tokens = float(self.capacity)
        self.last_refill_ts = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill_ts
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_per_second,
        )
        self.last_refill_ts = now

    def consume(self, on_exceed: str = "raise") -> None:
        """
        Consume one token. If no token available: raise ToolContractError when on_exceed=='raise',
        or block (sleep until refill) when on_exceed=='pause'. MVP: only 'raise' is used.
        """
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return
        if on_exceed == "raise":
            raise ToolContractError("rate limit exceeded")
        if on_exceed == "pause":
            # Sleep until at least one token is available
            wait = (1 - self.tokens) / self.refill_per_second
            if wait > 0:
                time.sleep(w)
            self._refill()
            self.tokens -= 1
            return
        raise ToolContractError("rate limit exceeded")


class ToolRateLimiter:
    """Per-tool rate limit state; call check before invoke."""

    def __init__(self) -> None:
        self._buckets: Dict[str, TokenBucket] = {}

    def check(
        self,
        tool_name: str,
        rate_limit: Optional[Dict[str, Any]],
        on_exceed: str = "raise",
    ) -> None:
        """
        Check/consume rate limit for tool. If descriptor has no rate_limit, no-op.
        Otherwise use or create a token bucket for this tool and consume one token.
        """
        if not rate_limit or not isinstance(rate_limit, dict):
            return
        rpm = rate_limit.get("requests_per_minute")
        if rpm is None:
            return
        rpm = int(rpm)
        if rpm <= 0:
            return
        burst = rate_limit.get("burst")
        if burst is not None:
            burst = int(burst)
        if tool_name not in self._buckets:
            self._buckets[tool_name] = TokenBucket(rpm, burst)
        self._buckets[tool_name].consume(on_exceed=on_exceed)
