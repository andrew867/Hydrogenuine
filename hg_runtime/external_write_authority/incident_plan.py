"""Phase 18 incident / rollback plan."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT
from hg_runtime.external_write_authority.schema import new_id, now_iso
from hg_runtime.external_write_authority.schema import new_id


@dataclass
class Phase18IncidentRollbackPlan:
    incident_plan_id: str
    scope_ref: str
    candidate_ref: str
    platform: str
    action_type: str
    rollback_available: bool
    rollback_method: str
    created_at: str
    operator_contact_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "incident_plan_id": self.incident_plan_id,
            "scope_ref": self.scope_ref,
            "candidate_ref": self.candidate_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "rollback_available": self.rollback_available,
            "rollback_method": self.rollback_method,
            "operator_contact_ref": self.operator_contact_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> Phase18IncidentRollbackPlan:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return Phase18IncidentRollbackPlan(**{**self.__dict__, "hash": compute_record_hash(body)})


def _plans_dir() -> Path:
    return PHASE18_ROOT / "incident_plans"


def create_incident_plan(
    *,
    scope_ref: str,
    candidate_ref: str,
    platform: str,
    action_type: str,
    rollback_available: bool = True,
    rollback_method: str = "platform_delete_if_supported",
    operator_contact_ref: str | None = "operator-local",
) -> Phase18IncidentRollbackPlan:
    plan = Phase18IncidentRollbackPlan(
        incident_plan_id=new_id("p18-incident"),
        scope_ref=scope_ref,
        candidate_ref=candidate_ref,
        platform=platform,
        action_type=action_type,
        rollback_available=rollback_available,
        rollback_method=rollback_method,
        operator_contact_ref=operator_contact_ref,
        created_at=now_iso(),
    ).with_hash()
    path = _plans_dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{plan.incident_plan_id}.json").write_text(json.dumps(plan.to_payload(), indent=2) + "\n", encoding="utf-8")
    return plan


def load_incident_plan(plan_id: str) -> Phase18IncidentRollbackPlan | None:
    path = _plans_dir() / f"{plan_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Phase18IncidentRollbackPlan(
        incident_plan_id=data["incident_plan_id"],
        scope_ref=data["scope_ref"],
        candidate_ref=data["candidate_ref"],
        platform=data["platform"],
        action_type=data["action_type"],
        rollback_available=data["rollback_available"],
        rollback_method=data["rollback_method"],
        operator_contact_ref=data.get("operator_contact_ref"),
        created_at=data["created_at"],
        hash=data.get("hash"),
    )


def find_incident_plan_for_scope(scope_ref: str) -> Phase18IncidentRollbackPlan | None:
    plans_dir = _plans_dir()
    if not plans_dir.is_dir():
        return None
    for p in sorted(plans_dir.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("scope_ref") == scope_ref:
            return load_incident_plan(data["incident_plan_id"])
    return None
