"""While-you-were-away digest — what changed since last operator view."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
STATE_PATH = WORKSPACE / ".hg-local" / "exciton" / "operator_seen.json"


def _load_seen() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {"last_operator_seen_at": None}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def mark_operator_seen() -> dict[str, Any]:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_operator_seen_at": datetime.now(timezone.utc).isoformat()}
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def build_away_digest(*, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    seen = _load_seen()
    since = seen.get("last_operator_seen_at")

    from hg_runtime.bounded_soak.active_run import assess_active_run
    from hg_runtime.exciton.soak_watchtower import build_soak_watchtower
    from hg_runtime.operator_action_queue.queue import open_default_queue

    soak = build_soak_watchtower(workspace=ws)
    active = assess_active_run(workspace=ws)
    queue = open_default_queue(ws)
    pending = len([i for i in queue.list_items() if i.status.value == "queued"])

    incidents: list[str] = []
    if soak.get("active_run_verdict", "").startswith("RED"):
        incidents.append(soak["active_run_verdict"])
    if soak.get("auto_publish_flip_detected"):
        incidents.append("legacy_auto_flip_detected")
    if soak.get("panic_file_present"):
        incidents.append("panic_active")
    if soak.get("stop_file_present"):
        incidents.append("stop_active")

    return {
        "schema": "exciton-away-digest",
        "since": since,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drafts_queued": soak.get("queued_item_count", 0),
        "pending_approvals": pending,
        "posts_published": soak.get("posts_published", 0),
        "incidents": incidents,
        "observer_gaps": [] if soak.get("observer_attached") else ["observer_missing"],
        "stop_panic": {
            "stop": soak.get("stop_file_present", False),
            "panic": soak.get("panic_file_present", False),
        },
        "active_run_state": active.get("verdict"),
        "pressure_to_approve": False,
        "human_summary": _summary(pending, incidents, active.get("verdict")),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _summary(pending: int, incidents: list[str], active_verdict: str | None) -> str:
    parts = [f"{pending} item(s) await review."]
    if incidents:
        parts.append(f"Incidents: {', '.join(incidents[:5])}.")
    if active_verdict and active_verdict.startswith("RED"):
        parts.append("Active run needs operator decision.")
    return " ".join(parts)


__all__ = ["build_away_digest", "mark_operator_seen"]
