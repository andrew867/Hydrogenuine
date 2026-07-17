"""Objective universe — bounded task scope for Agent Zero."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.task_selection.schema import (
    AllowedTaskType,
    BLOCKED_TASK_TYPES,
    STORE_ROOT,
    load_task_selection_policy,
    new_id,
    now_iso,
)

UNIVERSE_DIR = STORE_ROOT / "universes"


@dataclass
class ObjectiveScope:
    scope_id: str
    label: str
    allowed: bool = True


@dataclass
class ObjectiveUniverse:
    universe_id: str
    agent_id: str
    allowed_objective_scopes: tuple[str, ...]
    blocked_objective_scopes: tuple[str, ...]
    allowed_task_types: tuple[str, ...]
    blocked_task_types: tuple[str, ...]
    external_action_policy_ref: str
    status: str
    created_at: str
    expires_at: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "universe_id": self.universe_id,
            "agent_id": self.agent_id,
            "allowed_objective_scopes": list(self.allowed_objective_scopes),
            "blocked_objective_scopes": list(self.blocked_objective_scopes),
            "allowed_task_types": list(self.allowed_task_types),
            "blocked_task_types": list(self.blocked_task_types),
            "external_action_policy_ref": self.external_action_policy_ref,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> ObjectiveUniverse:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ObjectiveUniverse(**{**self.__dict__, "hash": compute_record_hash(body)})

    def scope_allowed(self, scope: str) -> bool:
        if scope in self.blocked_objective_scopes:
            return False
        return scope in self.allowed_objective_scopes

    def task_type_allowed(self, task_type: str) -> bool:
        if task_type in self.blocked_task_types or task_type in BLOCKED_TASK_TYPES:
            return False
        return task_type in self.allowed_task_types


def create_demo_universe(*, agent_id: str = "zero") -> ObjectiveUniverse:
    policy = load_task_selection_policy()
    allowed = tuple(t.value for t in AllowedTaskType if t != AllowedTaskType.IDLE_REFLECTION)
    blocked = tuple(BLOCKED_TASK_TYPES)
    scopes = (
        "internal:artifacts",
        "internal:receipts",
        "internal:queue",
        "internal:status",
        "internal:external_write_candidate",
    )
    universe = ObjectiveUniverse(
        universe_id=new_id("obj-universe"),
        agent_id=agent_id,
        allowed_objective_scopes=scopes,
        blocked_objective_scopes=("external:live_publish", "external:browser", "self:modify"),
        allowed_task_types=allowed,
        blocked_task_types=blocked,
        external_action_policy_ref="configs/agent_zero/external_write_authority_policy.json",
        status="active",
        created_at=now_iso(),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    ).with_hash()
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    (UNIVERSE_DIR / f"{universe.universe_id}.json").write_text(
        json.dumps(universe.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return universe


def load_universe(universe_id: str) -> ObjectiveUniverse | None:
    path = UNIVERSE_DIR / f"{universe_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ObjectiveUniverse(
        universe_id=data["universe_id"],
        agent_id=data["agent_id"],
        allowed_objective_scopes=tuple(data.get("allowed_objective_scopes") or ()),
        blocked_objective_scopes=tuple(data.get("blocked_objective_scopes") or ()),
        allowed_task_types=tuple(data.get("allowed_task_types") or ()),
        blocked_task_types=tuple(data.get("blocked_task_types") or ()),
        external_action_policy_ref=data.get("external_action_policy_ref", ""),
        status=data.get("status", "active"),
        created_at=data["created_at"],
        expires_at=data.get("expires_at"),
        hash=data.get("hash"),
    )


def list_universes() -> list[ObjectiveUniverse]:
    if not UNIVERSE_DIR.is_dir():
        return []
    return [load_universe(p.stem) for p in UNIVERSE_DIR.glob("*.json") if load_universe(p.stem)]
