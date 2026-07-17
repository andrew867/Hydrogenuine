"""Hands-off session schemas and enums."""

from __future__ import annotations

import json
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/hands_off_session_policy.json"
STORE_ROOT = WORKSPACE / ".hg-local/agent_zero/hands_off"


class HandsOffSessionStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    PANIC = "panic"
    FAILED_CLOSED = "failed_closed"


class HandsOffSessionVerdict(str, Enum):
    GREEN_SESSION_COMPLETE = "GREEN_HANDS_OFF_SESSION_COMPLETE"
    YELLOW_STOPPED_BY_OPERATOR = "YELLOW_HANDS_OFF_STOPPED_BY_OPERATOR"
    YELLOW_RESOURCE_THROTTLED = "YELLOW_HANDS_OFF_RESOURCE_THROTTLED"
    YELLOW_PROVIDER_UNAVAILABLE = "YELLOW_PROVIDER_UNAVAILABLE_HANDS_OFF_DEGRADED"
    YELLOW_LIVE_READ_UNAVAILABLE = "YELLOW_LIVE_READ_CREDENTIALS_MISSING_HANDS_OFF_CONTINUES"
    YELLOW_IDLE_REFLECTION = "YELLOW_OBJECTIVE_QUEUE_EMPTY_IDLE_REFLECTION"
    RED_FIXED_TURN_CAP = "RED_PHASE22_FIXED_TURN_CAP_PRESENT"
    RED_FIXED_DURATION_CAP = "RED_PHASE22_FIXED_DURATION_CAP_PRESENT"
    RED_SCHEDULER = "RED_PHASE22_CRON_OR_TIMER_CREATED"
    RED_DAEMON = "RED_PHASE22_DAEMON_OR_SERVICE_CREATED"
    RED_OVERLAP = "RED_PHASE22_OVERLAP_ALLOWED"
    RED_STOP_UNAVAILABLE = "RED_PHASE22_STOP_UNAVAILABLE"
    RED_PANIC_UNAVAILABLE = "RED_PHASE22_PANIC_UNAVAILABLE"
    RED_TURN_WITHOUT_RECEIPT = "RED_TURN_WITHOUT_RECEIPT"
    RED_TASK_SELECTION_WITHOUT_RECEIPT = "RED_TASK_SELECTION_WITHOUT_RECEIPT"
    RED_BROKER_BYPASSED = "RED_BROKER_BYPASSED"
    RED_EXTERNAL_SIDE_EFFECT = "RED_PHASE22_EXECUTES_LIVE_EXTERNAL_ACTION"
    RED_BUDGET_EXCEEDED = "RED_HANDS_OFF_BUDGET_EXCEEDED"


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def load_hands_off_policy() -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        return {}
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def session_dir(session_id: str, *, base: Path | None = None) -> Path:
    root = base or STORE_ROOT
    return root / session_id
