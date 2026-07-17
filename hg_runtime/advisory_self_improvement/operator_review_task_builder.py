"""Phase 25 advisory operator review task builder.

Each proposal produces an operator review task. A review task is NOT an
implementation, NOT an approval, and NOT a self-authorization. It only requests
that a human operator consider the proposal.
"""

from __future__ import annotations

from hg_runtime.advisory_self_improvement.schemas import assert_neutral, neutral_flags, record_hash


def build_operator_review_task(*, proposal_id: str, risk_level: str, title: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "advisory_operator_review_task_v1",
        "task_id": f"p25-review-{proposal_id}",
        "proposal_id": proposal_id,
        "risk_level": risk_level,
        "title": title,
        "status": "PENDING_OPERATOR_REVIEW",
        "doctrine_note": "A review task is not implementation, approval, or self-authorization.",
        "review_task_is_implementation": False,
        "review_task_is_approval": False,
        "proposal_is_self_authorization": False,
        "requires_human_operator": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_review_tasks(proposals: list[dict], risks: list[dict]) -> list[dict]:
    risk_by_proposal = {r["proposal_id"]: r["risk_level"] for r in risks}
    return [
        build_operator_review_task(
            proposal_id=p["proposal_id"],
            risk_level=risk_by_proposal.get(p["proposal_id"], "REQUIRES_OPERATOR_REVIEW"),
            title=p["title"],
        )
        for p in proposals
    ]
