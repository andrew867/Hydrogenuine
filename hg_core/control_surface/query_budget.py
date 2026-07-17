"""
Control Surface Pack 12: Query budgets per request to prevent expensive graph traversals.
"""
from __future__ import annotations

import threading
from typing import Optional

# Default max "cost" units per request (e.g. nodes visited, rows read)
DEFAULT_QUERY_BUDGET = 5000

_thread_local = threading.local()


def get_request_budget() -> int:
    """Return current request budget (thread-local). Default if not set."""
    return getattr(_thread_local, "query_budget", DEFAULT_QUERY_BUDGET)


def set_request_budget(value: Optional[int]) -> None:
    """Set thread-local request budget. None restores default."""
    if value is None:
        _thread_local.query_budget = DEFAULT_QUERY_BUDGET
    else:
        _thread_local.query_budget = value


def get_request_used() -> int:
    """Return current request used units (thread-local)."""
    return getattr(_thread_local, "query_used", 0)


def set_request_used(value: int) -> None:
    """Set thread-local used units (e.g. after a query)."""
    _thread_local.query_used = value


def consume_budget(units: int) -> bool:
    """
    Consume units from request budget. Returns False if would exceed budget (caller should abort).
    """
    used = get_request_used()
    budget = get_request_budget()
    if used + units > budget:
        return False
    set_request_used(used + units)
    return True


def reset_request_budget() -> None:
    """Reset used to 0 and budget to default (e.g. at start of request)."""
    set_request_budget(None)
    set_request_used(0)
