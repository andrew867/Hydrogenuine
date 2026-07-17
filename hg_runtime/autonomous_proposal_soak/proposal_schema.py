"""Repair proposal construction and specificity scoring."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.autonomous_proposal_soak.schemas import (
    ADVISORY_LABEL,
    BROKEN_ITEM_RECORD_SCHEMA,
    PATCH_CANDIDATE_RECORD_SCHEMA,
    REPAIR_PROPOSAL_SCHEMA,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)

UNKNOWN = "UNKNOWN"
GROUNDING_GROUNDED = "GROUNDED"
GROUNDING_PARTIAL = "PARTIAL"
GROUNDING_UNGROUNDED = "UNGROUNDED"
LOW_SPECIFICITY_STATUS = "LOW_SPECIFICITY_ADVISORY_NOT_READY"

GENERIC_PHRASES = (
    "review the code",
    "check dependencies",
    "update software",
    "add logging",
    "document findings",
    "repeat the test",
    "identify the issue",
    "resolve the issue",
    "ensure compatibility",
    "check configuration",
    "verify setup",
    "best practices",
    "known issue with the software",
)


def _as_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _known_items(value: Any) -> list[Any]:
    return [item for item in _as_list(value) if str(item).strip() and str(item).strip().upper() != UNKNOWN]


def _text_blob(payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for value in payload.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return "\n".join(parts).lower()


def generic_phrase_hits(text: str) -> list[str]:
    lower = text.lower()
    return [phrase for phrase in GENERIC_PHRASES if phrase in lower]


def _has_testable_acceptance_criterion(criteria: Any) -> bool:
    needles = ("test", "gate", "assert", "pytest", "records", "fails", "passes", "verdict")
    return any(any(needle in str(item).lower() for needle in needles) for item in _known_items(criteria))


def score_proposal(payload: Mapping[str, Any]) -> dict[str, Any]:
    affected_files = _known_items(payload.get("affected_files"))
    affected_tests = _known_items(payload.get("affected_tests"))
    reproduction_steps = _known_items(payload.get("reproduction_steps"))
    evidence_refs = _known_items(payload.get("evidence_refs"))
    acceptance_criteria = _known_items(payload.get("acceptance_criteria"))
    expected_actual = bool(str(payload.get("expected_behavior", "")).strip()) and bool(str(payload.get("actual_behavior", "")).strip())
    authority_boundary = str(payload.get("authority_risk", "")).strip().upper() != UNKNOWN
    receipt_or_proof = any("proof" in str(ref).lower() or "receipt" in str(ref).lower() for ref in evidence_refs)
    testable_acceptance = _has_testable_acceptance_criterion(acceptance_criteria)
    generic_hits = generic_phrase_hits(_text_blob(payload))

    specificity_score = 0
    specificity_score += 2 if affected_files else 0
    specificity_score += 2 if affected_tests else 0
    specificity_score += 2 if reproduction_steps else 0
    specificity_score += 2 if evidence_refs else 0
    specificity_score += 2 if expected_actual else 0
    specificity_score += 2 if testable_acceptance else 0
    specificity_score += 1 if authority_boundary else 0
    specificity_score += 1 if receipt_or_proof else 0

    genericity_score = len(generic_hits)
    genericity_score += 2 if not affected_files else 0
    genericity_score += 2 if not reproduction_steps else 0
    genericity_score += 2 if not evidence_refs else 0
    genericity_score += 2 if not testable_acceptance else 0

    if not evidence_refs:
        grounding_status = GROUNDING_UNGROUNDED
    elif affected_files and affected_tests and reproduction_steps:
        grounding_status = GROUNDING_GROUNDED
    else:
        grounding_status = GROUNDING_PARTIAL

    truncated = bool(payload.get("truncated")) or payload.get("finish_reason") == "length"
    advisory_marker_present = bool(payload.get("advisory_marker_present", True))
    ready = (
        specificity_score >= 8
        and genericity_score <= 3
        and bool(evidence_refs)
        and bool(affected_files)
        and bool(affected_tests)
        and bool(reproduction_steps)
        and testable_acceptance
        and grounding_status != GROUNDING_UNGROUNDED
        and not truncated
        and advisory_marker_present
    )
    status = "READY_FOR_SPEC_TESTS_PLANS" if ready else LOW_SPECIFICITY_STATUS
    return {
        "specificity_score": specificity_score,
        "genericity_score": genericity_score,
        "generic_phrase_hits": generic_hits,
        "grounding_status": grounding_status,
        "ready_for_spec_tests_plans": ready,
        "proposal_readiness_status": status,
        "testable_acceptance_criteria_present": testable_acceptance,
        "truncated": truncated,
        "advisory_marker_present": advisory_marker_present,
    }


def evaluate_organ_output(payload: Mapping[str, Any]) -> dict[str, Any]:
    scored = score_proposal(payload)
    return {
        "model_id": payload.get("model_id", UNKNOWN),
        "role": payload.get("role", UNKNOWN),
        "prompt_tokens": int(payload.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(payload.get("completion_tokens", 0) or 0),
        "total_tokens": int(payload.get("total_tokens", 0) or 0),
        "latency_ms": int(payload.get("latency_ms", 0) or 0),
        "finish_reason": payload.get("finish_reason", UNKNOWN),
        **scored,
        **neutral_flags(),
    }


def route_for_sharpening(payload: Mapping[str, Any]) -> dict[str, Any]:
    scored = score_proposal(payload)
    return {
        "route": "small_code_reviewer" if not scored["ready_for_spec_tests_plans"] else "small_doc_writer",
        "reason": "generic_or_ungrounded_output" if not scored["ready_for_spec_tests_plans"] else "ready_for_structured_proposal",
        **scored,
    }


def reviewer_sharpening_result(payload: Mapping[str, Any], *, reviewer_output: Mapping[str, Any] | None) -> dict[str, Any]:
    if reviewer_output is None:
        scored = score_proposal(payload)
        return {"sharpened": False, "status": LOW_SPECIFICITY_STATUS, **scored}
    scored = score_proposal(reviewer_output)
    return {"sharpened": scored["ready_for_spec_tests_plans"], **scored}


def broken_item(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("proposal_id", "title", "severity", "observed_failure", "expected_behavior", "actual_behavior"))
    data = dict(payload)
    reject_authority_payload(data)
    item = {
        "schema": BROKEN_ITEM_RECORD_SCHEMA,
        "proposal_id": data["proposal_id"],
        "title": data["title"],
        "severity": data["severity"],
        "phase_or_component": data.get("phase_or_component", ""),
        "observed_failure": data["observed_failure"],
        "expected_behavior": data["expected_behavior"],
        "actual_behavior": data["actual_behavior"],
        "authority_risk": data.get("authority_risk", "UNKNOWN"),
        "required_tests": list(data.get("required_tests", [])),
        **neutral_flags(),
    }
    item["item_hash"] = canonical_hash(item)
    return item


def repair_proposal(item: Mapping[str, Any], *, evidence_refs: list[str]) -> dict[str, Any]:
    affected_files = list(item.get("affected_files", ["hg_runtime/local_inference_organs/residency.py"]))
    affected_tests = list(
        item.get(
            "affected_tests",
            [
                "tests/autonomous_agent/test_phase33_6_local_multi_organ_inference_bus.py::small_doc_writer_can_reuse_loaded_tiny_model_under_max_loaded_three"
            ],
        )
    )
    affected_commands = list(item.get("affected_commands", ["python scripts/evals/autonomous_agent_phase_33_6_local_multi_organ_inference_bus_gate.py"]))
    proposal = {
        "schema": REPAIR_PROPOSAL_SCHEMA,
        "proposal_id": item["proposal_id"],
        "title": item["title"],
        "severity": item["severity"],
        "label": ADVISORY_LABEL,
        "phase_or_component": item.get("phase_or_component", UNKNOWN),
        "reproduction_steps": [
            "Run Phase 33.6 local multi-organ gate.",
            "Inspect gate_result.json for shared-model binding, finish_reason, and advisory marker fields.",
        ],
        "expected_behavior": item["expected_behavior"],
        "actual_behavior": item["actual_behavior"],
        "evidence_refs": list(evidence_refs),
        "affected_files": affected_files or [UNKNOWN],
        "affected_tests": affected_tests or [UNKNOWN],
        "affected_commands": affected_commands or [UNKNOWN],
        "authority_risk": item["authority_risk"],
        "external_side_effect_risk": "NONE_LOCAL_ONLY",
        "likely_root_cause": item.get(
            "likely_root_cause",
            "Role binding and output conformity policy need to distinguish shared model instances from organ roles.",
        ),
        "required_spec_changes": ["Document shared local model instance role bindings as advisory-only."],
        "required_test_changes": list(item.get("required_tests", [])),
        "required_implementation_changes": [
            "Reuse compatible loaded model instances for doc-writer and reviewer roles under max_loaded_models.",
            "Record finish_reason, truncation, and advisory marker conformance without converting output to authority.",
        ],
        "acceptance_criteria": [
            "P33.6 gate records shared_model_role_binding_used true.",
            "P33.6 gate remains GREEN only when required roles produce non-truncated advisory outputs.",
            "No external provider, 30B, DeepSeek, or security/offensive model is used.",
        ],
        "model_id": item.get("model_id", UNKNOWN),
        "role": item.get("role", "small_doc_writer"),
        "prompt_tokens": int(item.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(item.get("completion_tokens", 0) or 0),
        "total_tokens": int(item.get("total_tokens", 0) or 0),
        "latency_ms": int(item.get("latency_ms", 0) or 0),
        "finish_reason": item.get("finish_reason", "stop"),
        "truncated": bool(item.get("truncated", False)) or item.get("finish_reason") == "length",
        "advisory_marker_present": bool(item.get("advisory_marker_present", True)),
        "operator_next_step": "review_and_schedule_repair",
        **neutral_flags(),
    }
    proposal.update(score_proposal(proposal))
    proposal["proposal_hash"] = canonical_hash(proposal)
    return proposal


def patch_candidate_record(*, proposal_id: str, summary: str) -> dict[str, Any]:
    record = {
        "schema": PATCH_CANDIDATE_RECORD_SCHEMA,
        "proposal_id": proposal_id,
        "summary": summary,
        "applied": False,
        "committed": False,
        "patch_candidate_applied": False,
        "patch_candidate_committed": False,
        **neutral_flags(),
    }
    record["patch_candidate_hash"] = canonical_hash(record)
    return record


__all__ = [
    "GENERIC_PHRASES",
    "LOW_SPECIFICITY_STATUS",
    "broken_item",
    "evaluate_organ_output",
    "generic_phrase_hits",
    "patch_candidate_record",
    "repair_proposal",
    "reviewer_sharpening_result",
    "route_for_sharpening",
    "score_proposal",
]
