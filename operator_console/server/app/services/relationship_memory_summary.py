from __future__ import annotations

from typing import Any


def _runtime_tenant_id() -> str:
    import os

    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "recent_counterpart_count": 0,
        "dominant_relationship_type": None,
        "top_counterparts": [],
        "recent_relationship_events": [],
    }


def build_relationship_memory_summary(binding: dict[str, Any] | None = None) -> dict[str, Any]:
    binding = binding or {}
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    if not fingerprint_id:
        return _empty_summary()
    try:
        from hg_gateway.store import get_store
    except Exception:
        return _empty_summary()

    store = get_store()
    if not hasattr(store, "persona_autonomy_list"):
        return _empty_summary()

    try:
        items = store.persona_autonomy_list(_runtime_tenant_id(), fingerprint_id=fingerprint_id, hours=24.0 * 365.0, limit=50)
    except Exception:
        return _empty_summary()
    if not isinstance(items, list) or not items:
        return _empty_summary()

    relationship_counts: dict[str, int] = {}
    counterpart_counts: dict[str, int] = {}
    recent_events: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        relationship_type = str(row.get("relationship_type") or "").strip()
        counterpart = str(row.get("counterpart_fingerprint_id") or "").strip()
        if relationship_type:
            relationship_counts[relationship_type] = relationship_counts.get(relationship_type, 0) + 1
        if counterpart:
            counterpart_counts[counterpart] = counterpart_counts.get(counterpart, 0) + 1
        if relationship_type or counterpart:
            recent_events.append(
                {
                    "created_at": row.get("created_at"),
                    "relationship_type": relationship_type or None,
                    "counterpart_fingerprint_id": counterpart or None,
                    "engagement_mode": row.get("engagement_mode"),
                }
            )

    top_counterparts = [
        {"counterpart_fingerprint_id": counterpart, "count": count}
        for counterpart, count in sorted(counterpart_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]
    dominant_relationship_type = None
    if relationship_counts:
        dominant_relationship_type = max(
            relationship_counts.items(),
            key=lambda item: (item[1], item[0]),
        )[0]

    return {
        "status": "healthy",
        "recent_counterpart_count": len(counterpart_counts),
        "dominant_relationship_type": dominant_relationship_type,
        "top_counterparts": top_counterparts,
        "recent_relationship_events": recent_events[:5],
    }
