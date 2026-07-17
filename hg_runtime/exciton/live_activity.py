"""EXCITON Phase 2 — live activity / inference trace (operational, not chain-of-thought)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.exciton.soak_watchtower import active_soak_run_dir, build_soak_watchtower

WORKSPACE = Path(__file__).resolve().parents[2]


def _tail_jsonl(path: Path, n: int = 5) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def build_live_activity(*, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    soak = build_soak_watchtower(workspace=ws)
    run_dir = active_soak_run_dir()

    current_task = "idle"
    current_task_started_at: str | None = None
    last_output_summary = "no active task"
    last_receipt_hash: str | None = None
    last_error: str | None = None
    permit_decision = "NONE"
    tool_request_status = "idle"
    trust_boundary_result = "HELD"
    draft_id: str | None = None
    receipt_id: str | None = None
    current_provider = "local"
    model_id = "openvino-local"
    prompt_class = "status"
    input_source_summary = "subsystem probes"
    token_count: int | None = None
    latency_ms: int | None = None

    if soak.get("active") and run_dir:
        receipts = _tail_jsonl(run_dir / "soak_receipts.jsonl", 3)
        if receipts:
            last = receipts[-1]
            detail = last.get("detail") or last
            if isinstance(detail, str):
                last_output_summary = detail[:200]
            elif isinstance(detail, dict):
                last_output_summary = str(detail.get("summary") or detail.get("kind") or detail)[:200]
            else:
                last_output_summary = str(detail)[:200]
            receipt_id = last.get("receipt_id") or last.get("task_id")
            last_receipt_hash = (receipt_id or "")[:16] or None
            current_task = str(last.get("kind") or last.get("task_kind") or "soak_task")
            current_task_started_at = last.get("ts") or last.get("created_at")

        commands = _tail_jsonl(run_dir / "command_log.jsonl", 5)
        for ev in reversed(commands):
            if ev.get("event") == "CYCLE_COMPLETE":
                current_task = "soak_cycle"
                current_task_started_at = ev.get("ts")
                det = ev.get("detail") or {}
                last_output_summary = (
                    f"cycle complete elapsed={det.get('elapsed_min')} posts={det.get('posts_used')}"
                )
                break
            if ev.get("event") == "TASK":
                current_task = str((ev.get("detail") or {}).get("kind", "task"))
                break

        if soak.get("publish_enabled") and not soak.get("operator_confirmed_after_observation"):
            permit_decision = "DENY_UNCONFIRMED_OPERATOR"
            trust_boundary_result = "YELLOW_AWAITING_OPERATOR_CONFIRM"
        elif soak.get("publish_enabled"):
            permit_decision = "QUEUE_FOR_OPERATOR"
        elif soak.get("in_observation_window"):
            permit_decision = "OBSERVATION_NO_PUBLISH"

        social = _tail_jsonl(run_dir / "social_receipts.jsonl", 2)
        for s in social:
            if s.get("draft_id"):
                draft_id = s["draft_id"]
            if s.get("decision"):
                permit_decision = str(s["decision"])[:80]

    loop_state = "SOAK_RUNNING" if soak.get("active") else "IDLE"
    cycle_id = soak.get("run_id") if soak.get("active") else None

    return {
        "data_tier": "LIVE" if soak.get("active") else "LIVE_IDLE",
        "current_loop_state": loop_state,
        "current_cycle_id": cycle_id,
        "current_task": current_task,
        "current_task_started_at": current_task_started_at,
        "next_task_eta_seconds": soak.get("next_cycle_eta_seconds"),
        "current_provider": current_provider,
        "model_id": model_id,
        "prompt_class": prompt_class,
        "input_source_summary": input_source_summary,
        "trust_boundary_result": trust_boundary_result,
        "tool_request_status": tool_request_status,
        "permit_decision": permit_decision,
        "draft_id": draft_id,
        "receipt_id": receipt_id,
        "last_output_summary": last_output_summary,
        "completion_units": token_count,
        "latency_ms": latency_ms,
        "last_receipt_hash": last_receipt_hash,
        "last_error": last_error,
        "observer_verdict": soak.get("observer_verdict", "IDLE"),
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["build_live_activity"]
