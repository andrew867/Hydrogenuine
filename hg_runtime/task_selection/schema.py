"""Task selection schemas and enums."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/task_selection_policy.json"
STORE_ROOT = WORKSPACE / ".hg-local/task_selection"


class AllowedTaskType(str, Enum):
    REVIEW_LOCAL_ARTIFACTS = "review_local_artifacts"
    SUMMARIZE_RECENT_RECEIPTS = "summarize_recent_receipts"
    DRAFT_INTERNAL_NOTE = "draft_internal_note"
    INSPECT_QUEUE = "inspect_queue"
    PREPARE_EXTERNAL_ACTION_CANDIDATE = "prepare_external_action_candidate"
    RUN_LOCAL_STATUS_CHECK = "run_local_status_check"
    IDLE_REFLECTION = "idle_reflection"


BLOCKED_TASK_TYPES = frozenset({
    "publish_live",
    "send_live",
    "reply_live",
    "comment_live",
    "browse_live",
    "hardware_action",
    "self_modify_code",
    "self_merge",
    "disable_safety",
})


class TaskRefusalReason(str, Enum):
    OUT_OF_SCOPE = "out_of_scope"
    BLOCKED_TASK_TYPE = "blocked_task_type"
    EXTERNAL_ACTION_NOT_ALLOWED = "external_action_not_allowed"
    AUTHORITY_EXPANSION = "authority_expansion"
    MODEL_OUTPUT_NOT_AUTHORITY = "model_output_not_authority"
    LIVE_CONTENT_NOT_COMMAND = "live_content_not_command"
    STOP_PANIC_ACTIVE = "stop_panic_active"
    UNIVERSE_EXPIRED = "universe_expired"


class TaskSelectionVerdict(str, Enum):
    GREEN_TASK_SELECTED = "GREEN_TASK_SELECTED"
    GREEN_TASK_REFUSED = "GREEN_TASK_REFUSED"
    GREEN_IDLE_REFLECTION = "GREEN_IDLE_REFLECTION"
    YELLOW_OBJECTIVE_QUEUE_EMPTY = "YELLOW_OBJECTIVE_QUEUE_EMPTY_IDLE_REFLECTION"
    RED_TASK_SELECTED_OUTSIDE_UNIVERSE = "RED_TASK_SELECTED_OUTSIDE_OBJECTIVE_UNIVERSE"
    RED_TASK_SELECTION_EXPANDS_AUTHORITY = "RED_TASK_SELECTION_EXPANDS_AUTHORITY"
    RED_STOP_PANIC_NOT_CHECKED = "RED_STOP_PANIC_NOT_CHECKED"


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def load_task_selection_policy() -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        return {}
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
