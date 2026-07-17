"""P26 authority-boundary assertions."""

from __future__ import annotations

from collections.abc import Mapping

from hg_runtime.experience_ledger.schemas import assert_neutral


def assert_authority_boundary(record: Mapping) -> None:
    assert_neutral(record)


def boundary_summary() -> dict[str, bool]:
    return {
        "memory_is_not_truth": True,
        "recall_is_not_authority": True,
        "experience_is_not_evidence_by_itself": True,
        "ledger_entry_is_not_belief": True,
        "promotion_request_is_not_promotion": True,
        "operator_review_is_not_truth": True,
        "no_automatic_belief_promotion": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
    }

