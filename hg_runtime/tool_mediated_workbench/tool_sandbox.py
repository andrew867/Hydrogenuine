"""P29 tool sandbox result builder."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    SANDBOX_RESULT_STATES,
    ToolWorkbenchBoundaryError,
    assert_neutral,
    neutral_flags,
)


def build_sandbox_result(
    *,
    sandbox_id: str,
    request_id: str,
    plan_id: str,
    result_state: str,
    simulated_output: str | None = None,
    refusal_reason: str | None = None,
) -> dict:
    if result_state not in SANDBOX_RESULT_STATES:
        raise ToolWorkbenchBoundaryError(f"unknown_sandbox_result_state:{result_state}")
    record = {
        "record_type": "tool_sandbox_result_v1",
        "schema_version": "1",
        "sandbox_id": sandbox_id,
        "request_id": request_id,
        "plan_id": plan_id,
        "result_state": result_state,
        "simulated_output": simulated_output,
        "refusal_reason": refusal_reason,
        "sandbox_result_is_not_live_result": True,
        "dry_run_is_not_live_effect": True,
        "doctrine_note": "Sandbox result is not live result. Dry run is not live effect.",
        **neutral_flags(),
    }
    with_hash(record, "sandbox_hash")
    assert_neutral(record)
    return record
