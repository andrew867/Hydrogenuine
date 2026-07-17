"""Generalization results, receipts, and advisory hand-offs.

A result is the harness's verdict on a single held-out case. A green result is
only possible with a split record, a passing leakage audit, rubric-backed
evidence, and receipts. A failed result must link a failure memory ref so the
failure is remembered, not discarded. Domain-readiness hand-offs are advisory.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.generalization_eval.schemas import (
    GENERALIZATION_EVAL_RECEIPT_SCHEMA,
    GENERALIZATION_RESULT_SCHEMA,
    FAIL_LIKE,
    GREEN_LIKE,
    GeneralizationEvalError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)
from hg_runtime.generalization_eval.leakage import require_leakage_audit
from hg_runtime.generalization_eval.splits import require_split_record


def build_generalization_result(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("result_id", "case_ref", "split_ref", "status", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    require_split_record(data.get("split_ref"))
    status = str(data["status"]).strip().lower()
    evidence_refs = as_list(data, "evidence_refs")
    receipt_refs = as_list(data, "receipt_refs")

    if status in GREEN_LIKE:
        # A green result must survive the full chain: leakage audit, evidence,
        # receipts. The leakage check refuses a missing audit or a detected leak.
        require_leakage_audit(data.get("leakage_audit"))
        if not evidence_refs:
            raise GeneralizationEvalError("fake_green_rejected:unsupported_generalization")
        if not receipt_refs:
            raise GeneralizationEvalError("missing_receipt_blocks_success")
    elif status in FAIL_LIKE:
        if not str(data.get("failure_memory_ref", "")):
            raise GeneralizationEvalError("failed_transfer_requires_failure_memory_ref")

    return {
        "schema": GENERALIZATION_RESULT_SCHEMA,
        "result_id": data["result_id"],
        "case_ref": data["case_ref"],
        "split_ref": data["split_ref"],
        "status": status,
        "evidence_refs": evidence_refs,
        "receipt_refs": receipt_refs,
        "failure_memory_ref": data.get("failure_memory_ref"),
        "claim_boundary": data["claim_boundary"],
        "advisory_only": True,
        **neutral_flags(),
    }


def build_generalization_receipt(
    *,
    status: str,
    receipt_refs: list[str],
    case_refs: list[str] | None = None,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A green/passed generalization outcome cannot be recorded without receipts."""
    if str(status).lower() in GREEN_LIKE and not receipt_refs:
        raise GeneralizationEvalError("missing_receipt_blocks_success")
    receipt = {
        "schema": GENERALIZATION_EVAL_RECEIPT_SCHEMA,
        "status": status,
        "receipt_refs": list(receipt_refs),
        "case_refs": list(case_refs or []),
        "summary": dict(summary or {}),
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def build_domain_readiness(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Advisory hand-off. Readiness is evidence about tested scope, not a green light."""
    require_fields(payload, ("domain", "readiness", "evidence_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    data.setdefault("schema", "generalization_domain_readiness_v1")
    data["advisory_only"] = True
    data.update(neutral_flags())
    return data


__all__ = [
    "build_domain_readiness",
    "build_generalization_receipt",
    "build_generalization_result",
]
