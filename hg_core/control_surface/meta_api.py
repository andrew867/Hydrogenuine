"""
Control Surface Pack 11/12: Meta API — branding, freshness, cache_stats, query_budget.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from hg_core.integration import get_branding
from hg_core.ledger.ledger_writer import get_last_hash

from .cache_layer import get_cache_stats
from .query_budget import DEFAULT_QUERY_BUDGET, get_request_budget, get_request_used


def api_meta_branding(workspace_root: Path) -> Dict[str, Any]:
    """GET /api/meta/branding — returns UI branding placeholders and version info."""
    return get_branding(workspace_root)


def api_meta_freshness(
    workspace_root: Path,
    scope_type: str = "run",
    scope_id: str = "default",
) -> Dict[str, Any]:
    """GET /api/meta/freshness — last_event_id and freshness stats for UI badge and degrade-to-polling."""
    last_event_id = get_last_hash(Path(workspace_root), scope_type, scope_id)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "last_event_id": last_event_id,
        "freshness_ts": ts,
        "stream_healthy": True,
    }


def api_meta_cache_stats() -> Dict[str, Any]:
    """GET /api/meta/cache_stats — cache hit rates and sizes (admin)."""
    return get_cache_stats()


def api_meta_query_budget() -> Dict[str, Any]:
    """GET /api/meta/query_budget — current request budget and used (admin)."""
    return {
        "default_budget": DEFAULT_QUERY_BUDGET,
        "current_budget": get_request_budget(),
        "current_used": get_request_used(),
    }
