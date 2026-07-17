from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_gateway.operational_state_ledger import load_operational_json_state


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _delivery_requester_candidates(task_name: str, binding: dict[str, Any] | None = None) -> list[str]:
    binding = binding or {}
    candidates = [
        str(binding.get("operational_agent_id") or "").strip(),
        str(binding.get("operational_session_target") or "").strip(),
        str(binding.get("memory_namespace") or "").strip(),
        str(binding.get("knowledge_namespace") or "").strip(),
        task_name.strip(),
        f"automation-{task_name.strip()}",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.strip()
        if not key:
            continue
        lowered = key.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(key)
    return out


def build_research_delivery_summary(task_name: str, binding: dict[str, Any] | None = None, limit: int = 3) -> dict[str, Any]:
    root = _workspace_root()
    if root is None:
        return {
            "delivery_count": 0,
            "latest_delivery_at": None,
            "recent_deliveries": [],
        }
    state = load_operational_json_state(root, state_key="research_deliveries")
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    deliveries = payload.get("deliveries")
    if not isinstance(deliveries, list):
        deliveries = []
    targets = {item.lower() for item in _delivery_requester_candidates(task_name, binding=binding)}
    matched: list[dict[str, Any]] = []
    for item in reversed(deliveries):
        if not isinstance(item, dict):
            continue
        owner = str(item.get("requested_by") or "").strip().lower()
        if owner not in targets:
            continue
        matched.append(
            {
                "requested_by": str(item.get("requested_by") or "").strip() or None,
                "topic": str(item.get("topic") or "").strip() or None,
                "file_path": str(item.get("file_path") or "").strip() or None,
                "summary": str(item.get("summary") or "").strip() or None,
                "category": str(item.get("category") or "").strip() or None,
                "delivered_at": str(item.get("delivered_at") or "").strip() or None,
            }
        )
        if len(matched) >= max(1, min(limit, 10)):
            break
    return {
        "delivery_count": len(matched),
        "latest_delivery_at": next((item.get("delivered_at") for item in matched if item.get("delivered_at")), None),
        "recent_deliveries": matched,
    }
