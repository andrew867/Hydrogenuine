"""Provider budget, rate, and cost governor."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from hg_runtime.cloud_browser_governance.types import FIXTURE_CLOCK, advisory_envelope, stable_hash


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass
class TokenBudgetLedger:
    hourly_limit: int = field(default_factory=lambda: _env_int("HG_MAX_CLOUD_TOKENS_PER_HOUR", 50000))
    tokens_used: int = 0

    def record(self, tokens: int) -> dict[str, Any]:
        self.tokens_used += tokens
        pct = (self.tokens_used / self.hourly_limit * 100) if self.hourly_limit else 100
        return {"tokens_used": self.tokens_used, "hourly_limit": self.hourly_limit, "pct": pct}


@dataclass
class CostBudgetLedger:
    hourly_limit_usd: float = field(default_factory=lambda: _env_float("HG_HOURLY_CLOUD_BUDGET_USD", 0.50))
    daily_limit_usd: float = field(default_factory=lambda: _env_float("HG_DAILY_CLOUD_BUDGET_USD", 2.00))
    hourly_spent: float = 0.0
    daily_spent: float = 0.0

    def record(self, cost_usd: float) -> dict[str, Any]:
        self.hourly_spent += cost_usd
        self.daily_spent += cost_usd
        return {
            "hourly_spent": self.hourly_spent,
            "daily_spent": self.daily_spent,
            "hourly_limit_usd": self.hourly_limit_usd,
            "daily_limit_usd": self.daily_limit_usd,
        }


@dataclass
class ProviderRateLimiter:
    max_concurrent: int = 3
    max_per_minute: int = 20
    requests_this_minute: int = 0
    concurrent: int = 0

    def admit(self) -> tuple[bool, str]:
        if self.concurrent >= self.max_concurrent:
            return False, "concurrent_limit"
        if self.requests_this_minute >= self.max_per_minute:
            return False, "rate_limit"
        self.concurrent += 1
        self.requests_this_minute += 1
        return True, "ok"

    def release(self) -> None:
        self.concurrent = max(0, self.concurrent - 1)


@dataclass
class ProviderCircuitBreaker:
    failure_count: int = 0
    threshold: int = 5
    open: bool = False

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self.open = True

    def record_success(self) -> None:
        self.failure_count = 0
        self.open = False


class ProviderBudgetGovernor:
    WARN_THRESHOLDS = (50, 75, 90)

    def __init__(self) -> None:
        self.token_ledger = TokenBudgetLedger()
        self.cost_ledger = CostBudgetLedger()
        self.rate_limiter = ProviderRateLimiter()
        self.circuit_breaker = ProviderCircuitBreaker()
        self.warnings: list[str] = []

    def cloud_enabled(self) -> bool:
        return os.environ.get("HG_CLOUD_PROVIDERS_ENABLED", "false").strip().lower() in {"1", "true", "yes"}

    def check_budget(self, *, tokens: int = 0, cost_usd: float = 0.0, cost_unknown: bool = False) -> dict[str, Any]:
        if not self.cloud_enabled():
            return advisory_envelope(schema="budget-check", allowed=False, reason="cloud_disabled")
        if self.circuit_breaker.open:
            return advisory_envelope(schema="budget-check", allowed=False, reason="circuit_breaker_open")
        ok_rate, rate_reason = self.rate_limiter.admit()
        if not ok_rate:
            return advisory_envelope(schema="budget-check", allowed=False, reason=rate_reason)
        tok = self.token_ledger.record(tokens)
        cost = self.cost_ledger.record(cost_usd)
        hourly_pct = (self.cost_ledger.hourly_spent / self.cost_ledger.hourly_limit_usd * 100) if self.cost_ledger.hourly_limit_usd else 100
        daily_pct = (self.cost_ledger.daily_spent / self.cost_ledger.daily_limit_usd * 100) if self.cost_ledger.daily_limit_usd else 100
        token_pct = tok["pct"]
        for t, pct in (("hourly_cost", hourly_pct), ("daily_cost", daily_pct), ("hourly_tokens", token_pct)):
            for w in self.WARN_THRESHOLDS:
                if pct >= w:
                    self.warnings.append(f"{t}_warn_{w}")
        hard_stop = hourly_pct >= 100 or daily_pct >= 100 or token_pct >= 100
        if cost_unknown and not os.environ.get("HG_ALLOW_UNKNOWN_COST", "").strip().lower() in {"1", "true", "yes"}:
            return advisory_envelope(
                schema="budget-check",
                allowed=False,
                reason="unknown_cost_requires_approval",
                warnings=self.warnings,
            )
        if hard_stop:
            return advisory_envelope(schema="budget-check", allowed=False, reason="budget_hard_stop", hard_stop=True, warnings=self.warnings)
        receipt = advisory_envelope(
            schema="cloud-usage-receipt",
            allowed=True,
            tokens=tok,
            cost=cost,
            warnings=self.warnings,
            cost_unknown=cost_unknown,
            timestamp=FIXTURE_CLOCK,
        )
        receipt["receipt_hash"] = stable_hash(receipt)
        return receipt

    def release_request(self) -> None:
        self.rate_limiter.release()


__all__ = [
    "CostBudgetLedger",
    "ProviderBudgetGovernor",
    "ProviderCircuitBreaker",
    "ProviderRateLimiter",
    "TokenBudgetLedger",
]
