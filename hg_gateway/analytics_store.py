"""
Pack 15.5: Analytics queries for dashboards — summary counts, rule triggers. Tenant-scoped.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


def _window_to_iso(window: str) -> str:
    """Return ISO timestamp for (now - window). window: 24h, 7d, 30d."""
    now = datetime.now(timezone.utc)
    if window == "24h":
        delta = timedelta(hours=24)
    elif window == "7d":
        delta = timedelta(days=7)
    elif window == "30d":
        delta = timedelta(days=30)
    else:
        delta = timedelta(days=7)
    since = now - delta
    return since.isoformat().replace("+00:00", "Z")


def analytics_summary(tenant_id: str, window: str = "7d") -> Dict[str, Any]:
    """
    Return summary for tenant in window: signal_events_count, rule_triggers (per rule_id count).
    """
    from hg_gateway.db import get_connection

    since_iso = _window_to_iso(window)
    with get_connection() as conn:
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM signal_events WHERE tenant_id = ? AND timestamp >= ?",
            (tenant_id, since_iso),
        ).fetchone()
        signal_events_count = r["n"] or 0
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT rule_id, COUNT(*) AS cnt FROM rule_last_triggered
               WHERE tenant_id = ? AND last_triggered_at >= ?
               GROUP BY rule_id""",
            (tenant_id, since_iso),
        ).fetchall()
    rule_triggers = [{"rule_id": r["rule_id"], "count": r["cnt"]} for r in rows]

    return {
        "tenant_id": tenant_id,
        "window": window,
        "signal_events_count": signal_events_count,
        "rule_triggers": rule_triggers,
    }


def analytics_rules_triggers(
    tenant_id: str,
    *,
    from_ts: str | None = None,
    to_ts: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List rule trigger events for tenant (rule_id, chat_id, last_triggered_at)."""
    from hg_gateway.db import get_connection

    conditions = ["tenant_id = ?"]
    params: List[Any] = [tenant_id]
    if from_ts:
        conditions.append("last_triggered_at >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("last_triggered_at <= ?")
        params.append(to_ts)
    where = " AND ".join(conditions)
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT rule_id, chat_id, last_triggered_at FROM rule_last_triggered
                WHERE {where} ORDER BY last_triggered_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return [
        {"rule_id": r["rule_id"], "chat_id": r["chat_id"], "triggered_at": r["last_triggered_at"]}
        for r in rows
    ]
