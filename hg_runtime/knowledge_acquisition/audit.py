"""Mini-task result audit.

A raw mini-task (or workbench) result is never truth on its own. It must be
audited first, and a failing result is recorded as failed -- never hidden or
silently upgraded.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.knowledge_acquisition.schemas import (
    MINI_TASK_AUDIT_SCHEMA,
    KnowledgeAcquisitionError,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)

_PASS_OUTCOMES = {"passed", "pass", "verified"}
_FAIL_OUTCOMES = {"failed", "fail", "error", "regression"}


def audit_mini_task_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an audit record over a mini-task result.

    The audit fixes ``outcome`` to a recorded pass/fail and forbids a dry-run
    result claiming live completion.
    """
    require_fields(payload, ("task_id", "outcome", "auditor", "findings", "receipt_refs"))
    data = dict(payload)
    reject_authority_payload(data)

    outcome = str(data["outcome"]).lower()
    if outcome in _FAIL_OUTCOMES:
        # Failure is preserved, not laundered into success.
        data["passed"] = False
        data["recorded"] = True
        data["hidden"] = False
    elif outcome in _PASS_OUTCOMES:
        if not data.get("receipt_refs"):
            raise KnowledgeAcquisitionError("missing_receipt_blocks_success:audit_pass_requires_receipt")
        data["passed"] = True
        data["recorded"] = True
    else:
        raise KnowledgeAcquisitionError("schema_violation:invalid_audit_outcome")

    if data.get("result_mode") == "dry_run" and data.get("claims_live_completion"):
        raise KnowledgeAcquisitionError("fake_green_rejected:dry_run_cannot_claim_live_completion")

    data["audited"] = True
    data.setdefault("schema", MINI_TASK_AUDIT_SCHEMA)
    data.update(neutral_flags())
    return data


def trust_result(result: Mapping[str, Any], *, audit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A result may only be trusted as evidence once a passing audit exists."""
    if audit is None or not audit.get("audited"):
        raise KnowledgeAcquisitionError("mini_task_result_must_be_audited")
    if not audit.get("passed"):
        return {"trusted": False, "reason": "audit_recorded_failure", "result_ref": result.get("task_id")}
    return {"trusted": True, "result_ref": result.get("task_id"), "audit_ref": audit.get("task_id")}


__all__ = ["audit_mini_task_result", "trust_result"]
