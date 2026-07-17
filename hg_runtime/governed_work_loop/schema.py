"""Governed work loop schemas."""

from __future__ import annotations

import json
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/governed_work_loop_policy.json"
STORE_ROOT = WORKSPACE / ".hg-local/agent_zero/governed_work_loop"

ALLOWED_WORK_TYPES = frozenset({
    "inspect_queue",
    "review_local_artifacts",
    "summarize_recent_receipts",
    "draft_internal_note",
    "prepare_external_action_candidate",
    "request_external_authority",
    "dry_run_external_dispatch",
    "idle_reflection",
    "status_report",
})

BLOCKED_WORK_TYPES = frozenset({
    "publish_live_unscoped",
    "send_live_unscoped",
    "reply_live_unscoped",
    "comment_live_unscoped",
    "mass_message",
    "browser_live",
    "hardware_action",
    "self_modify_code",
    "self_merge",
    "disable_safety",
})


class GovernedWorkLoopVerdict(str, Enum):
    GREEN_WORK_COMPLETE = "GREEN_GOVERNED_WORK_COMPLETE"
    GREEN_WORK_REFUSED = "GREEN_GOVERNED_WORK_REFUSED"
    YELLOW_LIVE_ENVELOPE_NOT_ARMED = "YELLOW_LIVE_EXTERNAL_ACTION_ENVELOPE_NOT_ARMED"
    YELLOW_LIVE_BLOCKED_BY_POLICY = "YELLOW_LIVE_EXTERNAL_ACTIONS_BLOCKED_BY_POLICY"
    YELLOW_PROVIDER_UNAVAILABLE = "YELLOW_PROVIDER_UNAVAILABLE_GOVERNED_LOOP_DEGRADED"
    RED_UNSCOPED_LIVE = "RED_PHASE23_UNSCOPED_LIVE_EXTERNAL_ACTION"
    RED_AUTHORITY_EXPANSION = "RED_ZERO_EXPANDS_AUTHORITY"
    RED_BROKER_BYPASSED = "RED_CAPABILITY_BROKER_BYPASSED"
    RED_WORK_WITHOUT_RECEIPT = "RED_WORK_ITEM_WITHOUT_RECEIPT"


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def load_governed_work_policy() -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        return {}
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
