"""Advisory local organ bus envelopes and decision records."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.local_inference_organs.schemas import (
    ADVISORY_LABEL,
    ORGAN_BUS_MESSAGE_SCHEMA,
    ORGAN_DECISION_RECORD_SCHEMA,
    ORGAN_PROPOSAL_RECORD_SCHEMA,
    ORGAN_TASK_REQUEST_SCHEMA,
    ORGAN_TASK_RESULT_SCHEMA,
    LocalInferenceOrganError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


class LocalOrganBus:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []

    def message(self, payload: Mapping[str, Any], *, control: OperationControl | None = None) -> dict[str, Any]:
        preempt_if_needed(control)
        require_fields(payload, ("message_id", "organ_id", "receipt_refs"))
        data = dict(payload)
        reject_authority_payload(data)
        if not data.get("receipt_refs"):
            raise LocalInferenceOrganError("organ_bus_message_requires_receipt")
        msg = {
            "schema": ORGAN_BUS_MESSAGE_SCHEMA,
            "message_id": data["message_id"],
            "organ_id": data["organ_id"],
            "role": data.get("role"),
            "kind": data.get("kind", "task"),
            "payload_hash": canonical_hash(data.get("payload", {})),
            "receipt_refs": list(data.get("receipt_refs", [])),
            **neutral_flags(),
        }
        msg["message_hash"] = canonical_hash(msg)
        self.messages.append(msg)
        return msg

    def task_request(self, payload: Mapping[str, Any], *, control: OperationControl | None = None) -> dict[str, Any]:
        preempt_if_needed(control)
        require_fields(payload, ("task_id", "organ_id", "role", "prompt", "receipt_refs"))
        data = dict(payload)
        reject_authority_payload(data)
        if "shell" in str(data.get("prompt", "")).lower():
            raise LocalInferenceOrganError("small_coder_cannot_run_shell")
        req = {
            "schema": ORGAN_TASK_REQUEST_SCHEMA,
            "task_id": data["task_id"],
            "organ_id": data["organ_id"],
            "role": data["role"],
            "prompt_hash": canonical_hash({"prompt": data["prompt"]}),
            "receipt_refs": list(data.get("receipt_refs", [])),
            **neutral_flags(),
        }
        req["request_hash"] = canonical_hash(req)
        return req

    def task_result(self, payload: Mapping[str, Any], *, control: OperationControl | None = None) -> dict[str, Any]:
        preempt_if_needed(control)
        require_fields(payload, ("result_id", "task_id", "organ_id", "model_id", "output", "receipt_refs"))
        data = dict(payload)
        reject_authority_payload(data)
        output = str(data["output"])
        result = {
            "schema": ORGAN_TASK_RESULT_SCHEMA,
            "result_id": data["result_id"],
            "task_id": data["task_id"],
            "organ_id": data["organ_id"],
            "role": data.get("role"),
            "model_id": data["model_id"],
            "output": output,
            "output_hash": canonical_hash({"output": output}),
            "advisory_label": ADVISORY_LABEL,
            "receipt_refs": list(data.get("receipt_refs", [])),
            "latency_ms": data.get("latency_ms"),
            "finish_reason": data.get("finish_reason", ""),
            "truncated": bool(data.get("truncated", False)),
            "advisory_marker_present": bool(data.get("advisory_marker_present", ADVISORY_LABEL in output)),
            "structured_contract_valid": bool(data.get("structured_contract_valid", ADVISORY_LABEL in output)),
            "format_repair_retry": bool(data.get("format_repair_retry", False)),
            "format_repair_receipt": data.get("format_repair_receipt"),
            "format_repair_retry_count": int(data.get("format_repair_retry_count", 0) or 0),
            "max_tokens": data.get("max_tokens"),
            "success": bool(data.get("success", True)),
            **neutral_flags(),
        }
        result["result_hash"] = canonical_hash(result)
        self.results.append(result)
        return result

    def proposal_record(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        require_fields(payload, ("proposal_id", "source_result_ref", "summary"))
        data = dict(payload)
        reject_authority_payload(data)
        proposal = {
            "schema": ORGAN_PROPOSAL_RECORD_SCHEMA,
            "proposal_id": data["proposal_id"],
            "source_result_ref": data["source_result_ref"],
            "summary": str(data["summary"]),
            "is_patch": False,
            "is_merge": False,
            "requires_operator": True,
            **neutral_flags(),
        }
        proposal["proposal_hash"] = canonical_hash(proposal)
        return proposal

    def decision_record(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        require_fields(payload, ("decision_id", "input_task", "result_refs", "receipt_refs"))
        data = dict(payload)
        reject_authority_payload(data)
        if not data.get("receipt_refs"):
            raise LocalInferenceOrganError("organ_decision_record_requires_receipts")
        decision = {
            "schema": ORGAN_DECISION_RECORD_SCHEMA,
            "decision_id": data["decision_id"],
            "input_task": data["input_task"],
            "organs_consulted": list(data.get("organs_consulted", [])),
            "model_ids": list(data.get("model_ids", [])),
            "result_refs": list(data.get("result_refs", [])),
            "receipt_refs": list(data.get("receipt_refs", [])),
            "agreement": data.get("agreement", "mixed"),
            "disagreement": data.get("disagreement", ""),
            "operator_required_next_step": data.get("operator_required_next_step", "review_only"),
            "no_commit_performed": True,
            **neutral_flags(),
        }
        decision["decision_hash"] = canonical_hash(decision)
        self.decisions.append(decision)
        return decision


__all__ = ["LocalOrganBus"]
