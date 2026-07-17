from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_gateway.operational_state_ledger import load_operational_json_state


def build_action_rationale_summary(
    *,
    root: Path | None,
    task_name: str,
    session_target: str,
    binding: dict[str, Any] | None = None,
    research_delivery_summary: dict[str, Any] | None = None,
    agency_control_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = binding or {}
    if not root or not session_target:
        return {
            "status": "missing",
            "current_trigger": None,
            "current_goal": None,
            "reason_chain": [],
        }

    session_dir = root / "memory" / "automation" / session_target
    operational_target = str(binding.get("operational_session_target") or "").strip()
    operational_dir = root / "memory" / "automation" / operational_target if operational_target else session_dir

    state = load_operational_json_state(root, state_key=f"identity_continuity_state:{session_target}")
    state_payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    wake_receipt = state_payload.get("wake_receipt") if isinstance(state_payload.get("wake_receipt"), dict) else {}
    cadence_request = None
    if operational_dir:
        cadence_state = load_operational_json_state(root, state_key=f"operational_cadence_request:{operational_target}")
        cadence_request = cadence_state.get("payload") if isinstance(cadence_state.get("payload"), dict) else None
    initialization_memo_exists = bool(state_payload.get("initialization_memo_present"))
    agency_control_summary = agency_control_summary if isinstance(agency_control_summary, dict) else {}
    agency_mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    agency_reason = str(agency_control_summary.get("reason") or "").strip()

    current_goal = None
    dag_inputs = wake_receipt.get("dag_inputs") if isinstance(wake_receipt.get("dag_inputs"), dict) else {}
    if isinstance(dag_inputs, dict):
        current_goal = str(dag_inputs.get("goal") or "").strip() or None
    if not current_goal:
        current_goal = str(wake_receipt.get("wake_packet") or "").strip()[:240] or None

    reason_chain: list[str] = []
    current_trigger = "scheduled_wake"
    if agency_mode == "held":
        current_trigger = "agency_hold"
        reason_chain.append(f"agency_hold:{agency_reason or 'operator_hold'}")
    elif agency_mode == "review_only":
        current_trigger = "review_gate"
        reason_chain.append(f"review_gate:{agency_reason or 'operator_review_required'}")
    elif bool(agency_control_summary.get("outbound_budget_exhausted")):
        current_trigger = "outbound_budget"
        recent_count = agency_control_summary.get("recent_outbound_action_count")
        budget = agency_control_summary.get("daily_outbound_budget")
        if recent_count is not None and budget is not None:
            reason_chain.append(f"outbound_budget:{recent_count}/{budget}")
        else:
            reason_chain.append(f"outbound_budget:{agency_reason or 'budget_exhausted'}")
    if cadence_request:
        if current_trigger == "scheduled_wake":
            current_trigger = "cadence_override"
        cadence_reason = str(cadence_request.get("reason") or "").strip()
        if cadence_reason:
            reason_chain.append(f"cadence:{cadence_reason}")
    if current_goal:
        reason_chain.append(f"goal:{current_goal[:120]}")
    recent_delivery = None
    if isinstance(research_delivery_summary, dict):
        deliveries = research_delivery_summary.get("recent_deliveries")
        if isinstance(deliveries, list) and deliveries:
            recent_delivery = deliveries[0]
    if isinstance(recent_delivery, dict):
        topic = str(recent_delivery.get("topic") or "").strip()
        if topic:
            reason_chain.append(f"research:{topic}")
    if initialization_memo_exists and not reason_chain:
        current_trigger = "cold_start"
        reason_chain.append("cold_start:initialization_memo")
    if not reason_chain and wake_receipt:
        packet_hash = str(wake_receipt.get("wake_packet_hash") or "").strip()
        if packet_hash:
            reason_chain.append(f"wake_packet_hash:{packet_hash[:12]}")

    return {
        "status": "healthy" if reason_chain else "partial",
        "current_trigger": current_trigger,
        "current_goal": current_goal,
        "reason_chain": reason_chain[:5],
        "wake_completed_at": wake_receipt.get("wake_completed_at") or wake_receipt.get("timestamp"),
        "cadence_reason": str((cadence_request or {}).get("reason") or "").strip() or None,
        "agency_mode": agency_mode,
        "agency_reason": agency_reason or None,
    }
