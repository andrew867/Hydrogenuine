"""Phase 19 rollback and compensation — dry-run by default."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.action_ledger import (
    Phase19Verdict,
    load_ledger_entries,
    load_phase19_policy,
    phase18_live_proof_status,
)
from hg_runtime.external_write_authority.live_smoke import stop_panic_active
from hg_runtime.external_write_authority.schema import STORE_ROOT, new_id, now_iso

PHASE19_ROOT = STORE_ROOT / "phase19"
ROLLBACK_DIR = PHASE19_ROOT / "rollback"
COMPENSATION_DIR = PHASE19_ROOT / "compensation"


@dataclass
class RollbackPlan:
    rollback_plan_id: str
    ledger_entry_ref: str
    platform: str
    action_type: str
    rollback_supported: bool
    rollback_method: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "rollback_plan_id": self.rollback_plan_id,
            "ledger_entry_ref": self.ledger_entry_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "rollback_supported": self.rollback_supported,
            "rollback_method": self.rollback_method,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> RollbackPlan:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return RollbackPlan(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class RollbackAttempt:
    rollback_attempt_id: str
    rollback_plan_ref: str
    dry_run_only: bool
    external_side_effect: bool
    would_action: str
    created_at: str
    verdict: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "rollback_attempt_id": self.rollback_attempt_id,
            "rollback_plan_ref": self.rollback_plan_ref,
            "dry_run_only": self.dry_run_only,
            "external_side_effect": self.external_side_effect,
            "would_action": self.would_action,
            "created_at": self.created_at,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> RollbackAttempt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return RollbackAttempt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class CompensationActionPlan:
    compensation_plan_id: str
    ledger_entry_ref: str
    platform: str
    mitigation: str
    operator_action_required: bool
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "compensation_plan_id": self.compensation_plan_id,
            "ledger_entry_ref": self.ledger_entry_ref,
            "platform": self.platform,
            "mitigation": self.mitigation,
            "operator_action_required": self.operator_action_required,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> CompensationActionPlan:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return CompensationActionPlan(**{**self.__dict__, "hash": compute_record_hash(body)})


def build_rollback_plans() -> list[RollbackPlan]:
    ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
    plans: list[RollbackPlan] = []
    for entry in load_ledger_entries():
        if not entry.external_side_effect:
            continue
        supported = entry.platform == "moltbook" and entry.action_type == "publish_post"
        plan = RollbackPlan(
            rollback_plan_id=new_id("p19-rollback-plan"),
            ledger_entry_ref=entry.ledger_entry_id,
            platform=entry.platform,
            action_type=entry.action_type,
            rollback_supported=supported,
            rollback_method="platform_delete_if_supported" if supported else "operator_manual_mitigation",
            created_at=now_iso(),
        ).with_hash()
        (ROLLBACK_DIR / f"{plan.rollback_plan_id}.json").write_text(
            json.dumps(plan.to_payload(), indent=2) + "\n", encoding="utf-8"
        )
        plans.append(plan)
        if not supported:
            comp = CompensationActionPlan(
                compensation_plan_id=new_id("p19-comp"),
                ledger_entry_ref=entry.ledger_entry_id,
                platform=entry.platform,
                mitigation="Document incident; operator posts correction or contacts platform support",
                operator_action_required=True,
                created_at=now_iso(),
            ).with_hash()
            COMPENSATION_DIR.mkdir(parents=True, exist_ok=True)
            (COMPENSATION_DIR / f"{comp.compensation_plan_id}.json").write_text(
                json.dumps(comp.to_payload(), indent=2) + "\n", encoding="utf-8"
            )
    return plans


def dry_run_rollback(*, rollback_plan_id: str) -> RollbackAttempt | None:
    policy = load_phase19_policy()
    if stop_panic_active():
        return None
    path = ROLLBACK_DIR / f"{rollback_plan_id}.json"
    if not path.is_file():
        return None
    plan_data = json.loads(path.read_text(encoding="utf-8"))
    live_allowed = os.environ.get("HG_PHASE19_ALLOW_LIVE_ROLLBACK", "").lower() in ("1", "true", "yes")
    if live_allowed and not policy.get("live_rollback_allowed_by_default", False):
        pass  # still blocked in Phase 19 — live rollback never enabled here

    attempt = RollbackAttempt(
        rollback_attempt_id=new_id("p19-rollback-attempt"),
        rollback_plan_ref=rollback_plan_id,
        dry_run_only=True,
        external_side_effect=False,
        would_action=f"DELETE {plan_data.get('platform')} object (NOT EXECUTED)",
        created_at=now_iso(),
        verdict=Phase19Verdict.YELLOW_ROLLBACK_DRY,
    ).with_hash()
    attempts_dir = PHASE19_ROOT / "rollback_attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    (attempts_dir / f"{attempt.rollback_attempt_id}.json").write_text(
        json.dumps(attempt.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return attempt


def load_rollback_plans() -> list[RollbackPlan]:
    if not ROLLBACK_DIR.is_dir():
        return []
    plans: list[RollbackPlan] = []
    for path in ROLLBACK_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        plans.append(
            RollbackPlan(
                rollback_plan_id=data["rollback_plan_id"],
                ledger_entry_ref=data["ledger_entry_ref"],
                platform=data["platform"],
                action_type=data["action_type"],
                rollback_supported=data["rollback_supported"],
                rollback_method=data["rollback_method"],
                created_at=data["created_at"],
                hash=data.get("hash"),
            )
        )
    return plans
