"""Bounded soak schema — bounded session, stoppable, no hidden loops."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SOAK_SCHEMA_VERSION = "bounded-soak/1"


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def soak_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class SoakVerdict(str, Enum):
    COMPLETE = "COMPLETE"
    STOPPED = "STOPPED"
    PANIC = "PANIC"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    REFUSED = "REFUSED"


class SoakStopCondition(str, Enum):
    DURATION = "duration"
    PANIC_FILE = "panic_file"
    STOP_FILE = "stop_file"
    MAX_POSTS = "max_posts"
    OPERATOR_DENY = "operator_deny"


@dataclass
class SoakBudget:
    max_duration_minutes: int = 30
    hard_max_minutes: int = 60
    max_posts: int = 0
    max_tasks: int = 50

    def bounded(self) -> bool:
        return self.max_duration_minutes <= self.hard_max_minutes and self.max_tasks > 0


@dataclass
class BoundedSoakProfile:
    profile_id: str
    duration_minutes: int
    allow_live_social_read: bool
    allow_live_social_publish: bool
    max_posts: int
    operator_approval_required: bool
    tool_dry_run: bool
    cloud_disabled: bool = True
    live_browser: bool = False
    live_mic: bool = False
    playback: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "duration_minutes": self.duration_minutes,
            "allow_live_social_read": self.allow_live_social_read,
            "allow_live_social_publish": self.allow_live_social_publish,
            "max_posts": self.max_posts,
            "operator_approval_required": self.operator_approval_required,
            "tool_dry_run": self.tool_dry_run,
            "cloud_disabled": self.cloud_disabled,
            "live_browser": self.live_browser,
            "live_mic": self.live_mic,
            "playback": self.playback,
            **_frozen(),
        }


@dataclass
class SoakTask:
    task_id: str
    kind: str
    description: str

    def to_payload(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "kind": self.kind, "description": self.description, **_frozen()}


@dataclass
class SoakTaskResult:
    task_id: str
    kind: str
    ok: bool
    detail: str
    duration_ms: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "ok": self.ok,
            "detail": self.detail[:500],
            "duration_ms": self.duration_ms,
            **_frozen(),
        }


@dataclass
class SoakRun:
    run_id: str
    profile: BoundedSoakProfile
    started_at: str
    budget: SoakBudget
    tasks: list[SoakTask] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile.to_payload(),
            "started_at": self.started_at,
            "budget": {
                "max_duration_minutes": self.budget.max_duration_minutes,
                "hard_max_minutes": self.budget.hard_max_minutes,
                "max_posts": self.budget.max_posts,
                "max_tasks": self.budget.max_tasks,
                "bounded": self.budget.bounded(),
            },
            "tasks": [t.to_payload() for t in self.tasks],
            **_frozen(),
        }


@dataclass
class SoakReceipt:
    receipt_id: str
    run_id: str
    verdict: SoakVerdict
    stop_reason: str | None
    summary: str
    task_results: list[SoakTaskResult]
    created_at: str
    ewj_start_ref: str | None = None
    ewj_complete_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "soak-receipt",
            "version": SOAK_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "verdict": self.verdict.value,
            "stop_reason": self.stop_reason,
            "summary": self.summary[:2000],
            "task_results": [r.to_payload() for r in self.task_results],
            "created_at": self.created_at,
            "ewj_start_ref": self.ewj_start_ref,
            "ewj_complete_ref": self.ewj_complete_ref,
            **_frozen(),
        }
        payload["content_hash"] = soak_hash(payload)
        return payload


__all__ = [
    "SOAK_SCHEMA_VERSION",
    "BoundedSoakProfile",
    "SoakBudget",
    "SoakReceipt",
    "SoakRun",
    "SoakStopCondition",
    "SoakTask",
    "SoakTaskResult",
    "SoakVerdict",
    "new_id",
    "soak_hash",
]
