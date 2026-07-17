"""Phase 19 incident audit — bypass drills and readiness checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.action_ledger import load_phase19_policy
from hg_runtime.external_write_authority.schema import STORE_ROOT, new_id, now_iso

DRILL_DIR = STORE_ROOT / "phase19" / "bypass_drills"


@dataclass
class BypassDrillResult:
    drill_id: str
    drill_name: str
    passed: bool
    detail: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "drill_name": self.drill_name,
            "passed": self.passed,
            "detail": self.detail,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> BypassDrillResult:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return BypassDrillResult(**{**self.__dict__, "hash": compute_record_hash(body)})


def _save_drill(drill: BypassDrillResult) -> BypassDrillResult:
    DRILL_DIR.mkdir(parents=True, exist_ok=True)
    (DRILL_DIR / f"{drill.drill_id}.json").write_text(
        json.dumps(drill.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return drill


def run_bypass_drills() -> list[BypassDrillResult]:
    policy = load_phase19_policy()
    results: list[BypassDrillResult] = []

    # Review queue is not approval
    results.append(
        _save_drill(
            BypassDrillResult(
                drill_id=new_id("p19-drill"),
                drill_name="review_queue_not_approval",
                passed=policy.get("review_queue_is_approval") is False,
                detail="review_queue_is_approval must be false",
                created_at=now_iso(),
            ).with_hash()
        )
    )

    # Model output is not permission
    from hg_runtime.external_write_authority.broker_integration import create_candidate_from_broker_admission

    model_blocked = False
    try:
        create_candidate_from_broker_admission(
            run_id="drill-model",
            platform="moltbook",
            action_type="publish_post",
            content="x",
            scope="s",
            capability_decision_ref="model_output:approve",
        )
    except PermissionError:
        model_blocked = True
    results.append(
        _save_drill(
            BypassDrillResult(
                drill_id=new_id("p19-drill"),
                drill_name="model_output_not_permission",
                passed=model_blocked,
                detail="model_output cannot authorize candidate",
                created_at=now_iso(),
            ).with_hash()
        )
    )

    # EXCITON is not approval
    results.append(
        _save_drill(
            BypassDrillResult(
                drill_id=new_id("p19-drill"),
                drill_name="exciton_not_approval",
                passed=policy.get("exciton_is_approval") is False,
                detail="exciton_is_approval must be false",
                created_at=now_iso(),
            ).with_hash()
        )
    )

    # Broker refuses direct publish
    from hg_runtime.capability_broker.action_registry import is_forbidden_action

    results.append(
        _save_drill(
            BypassDrillResult(
                drill_id=new_id("p19-drill"),
                drill_name="broker_refuses_publish",
                passed=is_forbidden_action("publish"),
                detail="direct publish forbidden in broker",
                created_at=now_iso(),
            ).with_hash()
        )
    )

    # Expired/revoked permit drill (synthetic check)
    results.append(
        _save_drill(
            BypassDrillResult(
                drill_id=new_id("p19-drill"),
                drill_name="stale_permit_policy",
                passed=not policy.get("expired_permit_allowed") and not policy.get("revoked_permit_allowed"),
                detail="expired/revoked permits must not be allowed",
                created_at=now_iso(),
            ).with_hash()
        )
    )

    return results


def all_drills_passed(drills: list[BypassDrillResult]) -> bool:
    return all(d.passed for d in drills)
