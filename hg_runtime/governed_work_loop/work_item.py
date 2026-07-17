"""Governed work items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.governed_work_loop.schema import new_id, now_iso


@dataclass
class GovernedWorkItem:
    work_item_id: str
    task_selection_ref: str
    task_candidate_ref: str
    work_type: str
    scope_ref: str
    requires_broker: bool
    requires_external_candidate: bool
    requires_live_dispatch: bool
    status: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "work_item_id": self.work_item_id,
            "task_selection_ref": self.task_selection_ref,
            "task_candidate_ref": self.task_candidate_ref,
            "work_type": self.work_type,
            "scope_ref": self.scope_ref,
            "requires_broker": self.requires_broker,
            "requires_external_candidate": self.requires_external_candidate,
            "requires_live_dispatch": self.requires_live_dispatch,
            "status": self.status,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> GovernedWorkItem:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return GovernedWorkItem(**{**self.__dict__, "hash": compute_record_hash(body)})


TASK_TO_WORK = {
    "review_local_artifacts": "review_local_artifacts",
    "summarize_recent_receipts": "summarize_recent_receipts",
    "draft_internal_note": "draft_internal_note",
    "inspect_queue": "inspect_queue",
    "prepare_external_action_candidate": "prepare_external_action_candidate",
    "run_local_status_check": "status_report",
    "idle_reflection": "idle_reflection",
}


def create_work_item(
    *,
    task_selection_ref: str,
    task_candidate_ref: str,
    task_type: str,
    scope_ref: str,
    work_type: str | None = None,
) -> GovernedWorkItem:
    wt = work_type or TASK_TO_WORK.get(task_type, task_type)
    return GovernedWorkItem(
        work_item_id=new_id("gov-work-item"),
        task_selection_ref=task_selection_ref,
        task_candidate_ref=task_candidate_ref,
        work_type=wt,
        scope_ref=scope_ref,
        requires_broker=True,
        requires_external_candidate=wt == "prepare_external_action_candidate",
        requires_live_dispatch=wt in ("publish_live_unscoped", "send_live_unscoped"),
        status="pending",
        created_at=now_iso(),
    ).with_hash()
