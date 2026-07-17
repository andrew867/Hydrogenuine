"""Task candidates — proposals, not authority."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.task_selection.schema import AllowedTaskType, STORE_ROOT, new_id, now_iso

CANDIDATE_DIR = STORE_ROOT / "candidates"


@dataclass
class TaskCandidate:
    task_candidate_id: str
    objective_scope_ref: str
    task_type: str
    risk_class: str
    requires_external_action: bool
    requires_operator_review: bool
    status: str
    created_at: str
    title: str = ""
    description_ref: str | None = None
    source_ref: str | None = None
    provider_receipt_ref: str | None = None
    live_read_receipt_ref: str | None = None
    expires_at: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_candidate_id": self.task_candidate_id,
            "objective_scope_ref": self.objective_scope_ref,
            "task_type": self.task_type,
            "title": self.title,
            "description_ref": self.description_ref,
            "source_ref": self.source_ref,
            "provider_receipt_ref": self.provider_receipt_ref,
            "live_read_receipt_ref": self.live_read_receipt_ref,
            "risk_class": self.risk_class,
            "requires_external_action": self.requires_external_action,
            "requires_operator_review": self.requires_operator_review,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> TaskCandidate:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return TaskCandidate(**{**self.__dict__, "hash": compute_record_hash(body)})


def create_candidate(
    *,
    objective_scope: str,
    task_type: str,
    title: str = "",
    requires_external_action: bool = False,
    requires_operator_review: bool = False,
    source_ref: str | None = None,
    risk_class: str = "low",
) -> TaskCandidate:
    if not objective_scope:
        raise ValueError("objective scope required")
    if task_type == AllowedTaskType.PREPARE_EXTERNAL_ACTION_CANDIDATE.value:
        requires_external_action = False  # internal candidate only, not live
        requires_operator_review = True
    cand = TaskCandidate(
        task_candidate_id=new_id("task-cand"),
        objective_scope_ref=objective_scope,
        task_type=task_type,
        title=title or task_type,
        source_ref=source_ref,
        risk_class=risk_class,
        requires_external_action=requires_external_action,
        requires_operator_review=requires_operator_review,
        status="candidate",
        created_at=now_iso(),
    ).with_hash()
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    (CANDIDATE_DIR / f"{cand.task_candidate_id}.json").write_text(
        json.dumps(cand.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return cand


def seed_demo_candidates(universe_id: str) -> list[TaskCandidate]:
    return [
        create_candidate(
            objective_scope="internal:artifacts",
            task_type=AllowedTaskType.REVIEW_LOCAL_ARTIFACTS.value,
            title="Review local artifacts",
            source_ref=f"universe:{universe_id}",
        ),
        create_candidate(
            objective_scope="internal:receipts",
            task_type=AllowedTaskType.SUMMARIZE_RECENT_RECEIPTS.value,
            title="Summarize recent receipts",
        ),
        create_candidate(
            objective_scope="internal:queue",
            task_type=AllowedTaskType.INSPECT_QUEUE.value,
            title="Inspect operator review queue",
        ),
        create_candidate(
            objective_scope="internal:status",
            task_type=AllowedTaskType.RUN_LOCAL_STATUS_CHECK.value,
            title="Run local status check",
        ),
    ]


def load_candidate(candidate_id: str) -> TaskCandidate | None:
    path = CANDIDATE_DIR / f"{candidate_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return TaskCandidate(
        task_candidate_id=data["task_candidate_id"],
        objective_scope_ref=data["objective_scope_ref"],
        task_type=data["task_type"],
        title=data.get("title", ""),
        description_ref=data.get("description_ref"),
        source_ref=data.get("source_ref"),
        provider_receipt_ref=data.get("provider_receipt_ref"),
        live_read_receipt_ref=data.get("live_read_receipt_ref"),
        risk_class=data.get("risk_class", "low"),
        requires_external_action=data.get("requires_external_action", False),
        requires_operator_review=data.get("requires_operator_review", False),
        created_at=data["created_at"],
        expires_at=data.get("expires_at"),
        status=data.get("status", "candidate"),
        hash=data.get("hash"),
    )
