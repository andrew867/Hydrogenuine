"""P29 tool receipt builder."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import assert_neutral, neutral_flags


def build_tool_receipt(
    *,
    receipt_id: str,
    plan_id: str,
    sandbox_result_ids: list[str],
    refusal_ids: list[str],
    all_dry_run: bool = True,
    operator_approval_pending: bool = True,
) -> dict:
    record = {
        "record_type": "tool_receipt_v1",
        "schema_version": "1",
        "receipt_id": receipt_id,
        "plan_id": plan_id,
        "sandbox_result_ids": list(sandbox_result_ids),
        "refusal_ids": list(refusal_ids),
        "all_dry_run": all_dry_run,
        "operator_approval_pending": operator_approval_pending,
        "tool_receipt_is_not_authority": True,
        "doctrine_note": "Tool receipt is not authority.",
        **neutral_flags(),
    }
    with_hash(record, "receipt_hash")
    assert_neutral(record)
    return record
