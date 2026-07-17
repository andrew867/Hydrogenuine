from __future__ import annotations

from typing import Any

from hg_core.affective.api import (
    get_current_regulatory_state,
    get_regulatory_policy,
    list_applied_modulations,
    list_regulatory_overrides,
)


def _runtime_tenant_id() -> str:
    import os

    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _top_key(mapping: Any) -> str | None:
    if not isinstance(mapping, dict) or not mapping:
        return None
    valid = [(str(key), value) for key, value in mapping.items() if key not in (None, "")]
    if not valid:
        return None
    return max(valid, key=lambda item: item[1] if isinstance(item[1], (int, float)) else 0)[0]


def _empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "continuity_anchor": None,
        "fingerprint_id": None,
        "affective_state": {},
        "affective_policy": {},
        "active_overrides": [],
        "applied_modulations": [],
        "action_state": {},
        "latest_turn": None,
        "summary": "no affect/action signals available",
    }


def _latest_turn_snapshot(turn: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(turn, dict) or not turn:
        return None
    return {
        "turn_id": turn.get("turn_id"),
        "created_at": turn.get("created_at"),
        "arc_state": turn.get("arc_state"),
        "engagement_mode": turn.get("engagement_mode"),
        "depth_level": turn.get("depth_level"),
        "uncertainty_level": turn.get("uncertainty_level"),
        "relationship_type": turn.get("relationship_type"),
        "counterpart_fingerprint_id": turn.get("counterpart_fingerprint_id"),
        "callback_surface": bool(turn.get("callback_surface")),
        "proactive_notice": bool(turn.get("proactive_notice")),
        "position_evolution": bool(turn.get("position_evolution")),
        "lateral_mode": turn.get("lateral_mode"),
        "detail_keys": sorted((turn.get("details") or {}).keys()) if isinstance(turn.get("details"), dict) else [],
    }


def build_affect_action_summary(
    *,
    root: Any | None,
    task_name: str,
    session_target: str,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = binding or {}
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    continuity_anchor = str(binding.get("operational_agent_id") or "").strip() or str(task_name or "").strip()
    if not root or not fingerprint_id or not continuity_anchor:
        return _empty_summary()

    try:
        from hg_gateway.store import get_store
    except Exception:
        return _empty_summary()

    try:
        store = get_store()
    except Exception:
        return _empty_summary()

    tenant_id = _runtime_tenant_id()
    autonomy_summary = {}
    autonomy_items: list[dict[str, Any]] = []
    if hasattr(store, "persona_autonomy_summary"):
        try:
            autonomy_summary = store.persona_autonomy_summary(tenant_id, fingerprint_id=fingerprint_id, hours=24.0 * 365.0)
        except Exception:
            autonomy_summary = {}
    if hasattr(store, "persona_autonomy_list"):
        try:
            autonomy_items = store.persona_autonomy_list(tenant_id, fingerprint_id=fingerprint_id, hours=24.0 * 365.0, limit=50)
        except Exception:
            autonomy_items = []

    latest_turn = _latest_turn_snapshot(autonomy_items[0] if autonomy_items else None)
    current_regulatory_state = get_current_regulatory_state(root, "agent", continuity_anchor, agent_id=continuity_anchor)
    regulatory_state = current_regulatory_state.get("state") if isinstance(current_regulatory_state, dict) else {}
    regulatory_state = regulatory_state if isinstance(regulatory_state, dict) else {}
    regulatory_policy = get_regulatory_policy(root)
    active_overrides = list_regulatory_overrides(root, scope_type="agent", scope_id=continuity_anchor, active_only=True, limit=10)
    applied_modulations = list_applied_modulations(root, scope_type="agent", scope_id=continuity_anchor, agent_id=continuity_anchor, limit=10)

    action_state = {
        "total_turns": int(autonomy_summary.get("total_turns") or 0),
        "dominant_arc_state": _top_key(autonomy_summary.get("arc_distribution")),
        "dominant_engagement_mode": _top_key(autonomy_summary.get("engagement_distribution")),
        "dominant_uncertainty_level": _top_key(autonomy_summary.get("uncertainty_distribution")),
        "dominant_relationship_type": _top_key(autonomy_summary.get("relationship_distribution")),
        "callback_rate": float(autonomy_summary.get("callback_rate") or 0.0),
        "proactive_notice_rate": float(autonomy_summary.get("proactive_notice_rate") or 0.0),
        "position_evolution_rate": float(autonomy_summary.get("position_evolution_rate") or 0.0),
    }

    affective_state = {
        "status": "healthy" if (regulatory_state or active_overrides or applied_modulations or regulatory_policy) else "partial",
        "trust_band": regulatory_state.get("trust_band"),
        "agency_budget": regulatory_state.get("agency_budget"),
        "escrow_locked": regulatory_state.get("escrow_locked"),
        "incident_points": regulatory_state.get("incident_points"),
        "current_regulatory_state": current_regulatory_state,
    }

    status = "healthy"
    if not action_state["total_turns"] and affective_state["status"] != "healthy":
        status = "missing"
    elif not action_state["total_turns"] or affective_state["status"] != "healthy":
        status = "partial"

    summary_bits = []
    if action_state["dominant_engagement_mode"]:
        summary_bits.append(f"action:{action_state['dominant_engagement_mode']}")
    if affective_state["trust_band"] is not None:
        summary_bits.append(f"trust:{affective_state['trust_band']}")
    if affective_state["agency_budget"] is not None:
        summary_bits.append(f"budget:{affective_state['agency_budget']}")

    return {
        "status": status,
        "continuity_anchor": continuity_anchor,
        "fingerprint_id": fingerprint_id,
        "affective_state": affective_state,
        "affective_policy": regulatory_policy if isinstance(regulatory_policy, dict) else {},
        "active_overrides": active_overrides,
        "applied_modulations": applied_modulations,
        "action_state": action_state,
        "latest_turn": latest_turn,
        "summary": ", ".join(summary_bits) if summary_bits else "affect_action_ready",
    }
