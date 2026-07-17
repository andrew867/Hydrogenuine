from __future__ import annotations

from typing import Any


def build_identity_resume_procedure(
    *,
    identity_continuity_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}

    open_steps: list[str] = []
    completed_steps: list[str] = []

    if identity_continuity_summary.get("initialization_memo_present"):
        completed_steps.append("initialization_memo_present")
    else:
        open_steps.append("write_initialization_memo")

    if identity_continuity_summary.get("wake_receipt_present") or identity_continuity_summary.get("last_wake_at"):
        completed_steps.append("wake_receipt_present")
    else:
        open_steps.append("record_wake_receipt")

    if identity_continuity_summary.get("sleep_summary_present") or identity_continuity_summary.get("last_sleep_at"):
        completed_steps.append("sleep_summary_present")
    else:
        open_steps.append("record_sleep_summary")

    status = "ready" if not open_steps else ("missing" if len(open_steps) == 3 else "partial")
    return {
        "status": status,
        "open_step_count": len(open_steps),
        "completed_step_count": len(completed_steps),
        "open_steps": open_steps,
        "completed_steps": completed_steps,
        "summary": open_steps[0] if open_steps else "identity_resume_ready",
    }
