from __future__ import annotations

from typing import Any


def _runtime_tenant_id() -> str:
    import os

    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "total_turns": 0,
        "dominant_arc_state": None,
        "dominant_engagement_mode": None,
        "dominant_uncertainty": None,
        "callback_rate": 0.0,
        "proactive_notice_rate": 0.0,
        "position_evolution_rate": 0.0,
        "relationship_signal": None,
    }


def _top_key(mapping: Any) -> str | None:
    if not isinstance(mapping, dict) or not mapping:
        return None
    valid = [(str(key), value) for key, value in mapping.items() if key not in (None, "")]
    if not valid:
        return None
    return max(valid, key=lambda item: item[1] if isinstance(item[1], (int, float)) else 0)[0]


def build_self_model_summary(binding: dict[str, Any] | None = None) -> dict[str, Any]:
    binding = binding or {}
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    if not fingerprint_id:
        return _empty_summary()
    try:
        from hg_gateway.store import get_store
    except Exception:
        return _empty_summary()

    store = get_store()
    if not hasattr(store, "persona_autonomy_summary"):
        return _empty_summary()

    try:
        summary = store.persona_autonomy_summary(_runtime_tenant_id(), fingerprint_id=fingerprint_id, hours=24.0 * 365.0)
    except Exception:
        return _empty_summary()
    if not isinstance(summary, dict):
        return _empty_summary()

    total_turns = int(summary.get("total_turns") or 0)
    if total_turns <= 0:
        return _empty_summary()

    relationship_distribution = summary.get("relationship_distribution") if isinstance(summary.get("relationship_distribution"), dict) else {}
    return {
        "status": "healthy",
        "total_turns": total_turns,
        "dominant_arc_state": _top_key(summary.get("arc_distribution")),
        "dominant_engagement_mode": _top_key(summary.get("engagement_distribution")),
        "dominant_uncertainty": _top_key(summary.get("uncertainty_distribution")),
        "uncertainty_distribution": summary.get("uncertainty_distribution") if isinstance(summary.get("uncertainty_distribution"), dict) else {},
        "callback_rate": float(summary.get("callback_rate") or 0.0),
        "proactive_notice_rate": float(summary.get("proactive_notice_rate") or 0.0),
        "position_evolution_rate": float(summary.get("position_evolution_rate") or 0.0),
        "relationship_signal": _top_key(relationship_distribution),
    }
