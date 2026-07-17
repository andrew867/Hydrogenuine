"""
Pack 15.4: Store for monitor_rules and rule_last_triggered. List rules, get features for chat, cooldown.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from hg_gateway.db import get_connection
from hg_gateway.monitoring_rules import (
    RULE_ACTIONS,
    default_rules_v1,
    evaluate_condition,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_default_rules(conn: Any) -> None:
    """Seed default rules (v1) if no rules exist."""
    r = conn.execute("SELECT COUNT(*) AS n FROM monitor_rules").fetchone()
    if (r["n"] or 0) == 0:
        now = _now()
        for rule in default_rules_v1():
            conn.execute(
                """INSERT OR IGNORE INTO monitor_rules
                (rule_id, tenant_id, enabled, condition_json, action, message_template, cooldown_seconds, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule["rule_id"],
                    rule.get("tenant_id"),
                    1 if rule.get("enabled", True) else 0,
                    json.dumps(rule["condition"]),
                    rule["action"],
                    rule.get("message_template") or "",
                    int(rule.get("cooldown_seconds", 60)),
                    now,
                    now,
                ),
            )


def monitor_rules_list(tenant_id: str, include_global: bool = True) -> List[Dict[str, Any]]:
    """List enabled monitor rules for tenant (and global if include_global)."""
    with get_connection() as conn:
        _ensure_default_rules(conn)
        if include_global:
            rows = conn.execute(
                """SELECT rule_id, tenant_id, enabled, condition_json, action, message_template, cooldown_seconds, updated_at
                   FROM monitor_rules WHERE (tenant_id = ? OR tenant_id IS NULL) AND enabled = 1
                   ORDER BY (tenant_id IS NULL), tenant_id, rule_id""",
                (tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT rule_id, tenant_id, enabled, condition_json, action, message_template, cooldown_seconds, updated_at
                   FROM monitor_rules WHERE tenant_id = ? AND enabled = 1 ORDER BY rule_id""",
                (tenant_id,),
            ).fetchall()
        out = []
        for r in rows:
            out.append({
                "rule_id": r["rule_id"],
                "tenant_id": r["tenant_id"],
                "enabled": bool(r["enabled"]),
                "condition": json.loads(r["condition_json"]) if r["condition_json"] else {},
                "action": r["action"],
                "message_template": r["message_template"] or "",
                "cooldown_seconds": int(r["cooldown_seconds"]),
                "updated_at": r["updated_at"],
            })
        return out


def get_features_for_chat(tenant_id: str, chat_id: str, limit_events: int = 10) -> Tuple[Dict[str, float], List[str]]:
    """
    Get merged feature_key -> value from the most recent signal_events for this chat.
    Returns (features dict, list of event_ids used).
    """
    with get_connection() as conn:
        events = conn.execute(
            """SELECT event_id FROM signal_events
               WHERE tenant_id = ? AND chat_id = ? ORDER BY timestamp DESC LIMIT ?""",
            (tenant_id, chat_id, limit_events),
        ).fetchall()
        event_ids = [r["event_id"] for r in events]
        if not event_ids:
            return {}, []
        placeholders = ",".join("?" * len(event_ids))
        rows = conn.execute(
            f"""SELECT event_id, feature_key, feature_value FROM signal_features
                WHERE event_id IN ({placeholders})""",
            event_ids,
        ).fetchall()
        features: Dict[str, float] = {}
        for r in rows:
            # first occurrence wins (we order by event desc, so older events first in rows; we want latest)
            key = r["feature_key"]
            if key not in features:
                features[key] = float(r["feature_value"])
        return features, event_ids


def is_rule_in_cooldown(rule_id: str, tenant_id: str, chat_id: str, cooldown_seconds: int) -> bool:
    """True if this rule was triggered for this tenant/chat within cooldown_seconds."""
    if cooldown_seconds <= 0:
        return False
    with get_connection() as conn:
        r = conn.execute(
            """SELECT last_triggered_at FROM rule_last_triggered
               WHERE rule_id = ? AND tenant_id = ? AND chat_id = ?""",
            (rule_id, tenant_id, chat_id),
        ).fetchone()
        if not r:
            return False
        from datetime import datetime
        try:
            triggered = datetime.fromisoformat(r["last_triggered_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - triggered).total_seconds() < cooldown_seconds
        except Exception:
            return False


def record_rule_triggered(rule_id: str, tenant_id: str, chat_id: str) -> None:
    """Record that this rule fired for tenant/chat (for cooldown)."""
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO rule_last_triggered (rule_id, tenant_id, chat_id, last_triggered_at)
               VALUES (?, ?, ?, ?)""",
            (rule_id, tenant_id, chat_id, now),
        )


def evaluate_rules_after_turn(
    tenant_id: str,
    chat_id: str,
) -> List[Dict[str, Any]]:
    """
    Get recent signal features for chat, evaluate all enabled rules, apply cooldown.
    Returns list of fired rules: [{"rule_id", "action", "message_template", "evidence_refs", "signals"}, ...].
    """
    features, event_ids = get_features_for_chat(tenant_id, chat_id)
    if not features:
        return []
    rules = monitor_rules_list(tenant_id, include_global=True)
    fired = []
    for rule in rules:
        action = rule.get("action") or "warn"
        if action not in RULE_ACTIONS:
            continue
        if is_rule_in_cooldown(rule["rule_id"], tenant_id, chat_id, rule.get("cooldown_seconds", 60)):
            continue
        if not evaluate_condition(rule.get("condition") or {}, features):
            continue
        record_rule_triggered(rule["rule_id"], tenant_id, chat_id)
        fired.append({
            "rule_id": rule["rule_id"],
            "action": action,
            "message_template": rule.get("message_template") or "",
            "evidence_refs": event_ids[:5],
            "signals": list(features.keys()),
        })
    return fired
