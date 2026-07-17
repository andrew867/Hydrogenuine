"""Local Inference QA Orchestrator response parser."""

from __future__ import annotations

from hg_runtime.local_inference_qa_orchestrator.schemas import (
    QAOrchestratorError,
    _stable_hash,
    reject_qa_overreach,
)


def parse_model_response(
    prompt: dict,
    response_text: str,
    model_id: str | None = None,
) -> dict:
    return {
        "prompt_id": prompt["prompt_id"],
        "prompt_hash": prompt["prompt_hash"],
        "model_id": model_id,
        "response_text": response_text,
        "response_hash": _stable_hash({"text": response_text}),
        "output_not_truth": True,
        "local_inference_not_authority": True,
        "willingness_not_permission": True,
    }


def extract_hypothesis(response: dict, subsystem: str, issue: str) -> dict:
    reject_qa_overreach({})
    return {
        "hypothesis_id": f"hyp-{response['response_hash'][:8]}",
        "affected_subsystem": subsystem,
        "suspected_issue": issue,
        "evidence_references": [],
        "uncertainty": "high",
        "severity_suggestion": "unknown",
        "operator_review_required": True,
        "hypothesis_is_not_evidence_by_itself": True,
        "output_not_truth": True,
    }


def extract_test_suggestion(response: dict, target: str, reason: str) -> dict:
    reject_qa_overreach({})
    return {
        "suggested_test_id": f"ts-{response['response_hash'][:8]}",
        "target_package": target,
        "reason": reason,
        "expected_failure_mode": "unknown",
        "safety_class": "boundary",
        "operator_review_required": True,
        "suggestion_is_not_test_authority": True,
        "output_not_truth": True,
    }


def extract_repair_recommendation(response: dict, affected: str, outline: str) -> dict:
    reject_qa_overreach({})
    return {
        "recommendation_id": f"rec-{response['response_hash'][:8]}",
        "affected_subsystem": affected,
        "proposed_investigation": outline,
        "proposed_repair_outline": outline,
        "risk": "unknown",
        "confidence_uncertainty": "high_uncertainty",
        "operator_review_required": True,
        "is_permission": False,
        "is_patch_approval": False,
        "authorizes_tools": False,
        "advisory_only": True,
    }


def extract_proof_audit_summary(response: dict, bundle: str) -> dict:
    reject_qa_overreach({})
    return {
        "proof_bundle_inspected": bundle,
        "possible_gap": response.get("response_text", "")[:200],
        "evidence_references": [],
        "status": "advisory",
        "proof_mutated": False,
        "operator_review_required": True,
        "output_not_truth": True,
    }


def check_response_boundary(response_text: str) -> dict:
    payload = {}
    lower = response_text.lower()
    if "authorize" in lower and "tool" in lower:
        payload["tool_authorized"] = True
    if "enable" in lower and "provider" in lower:
        payload["external_provider_enabled"] = True
    if ".hg-local" in lower or "hg_local" in lower:
        payload["hg_local_touched"] = True
    if "agi" in lower and ("achieved" in lower or "is agi" in lower or "claim" in lower):
        payload["claims_agi"] = True
    if "deploy" in lower and ("permission" in lower or "ready" in lower or "approved" in lower):
        payload["deployment_permission_claimed"] = True
    if "green" in lower and ("mark" in lower or "infer" in lower or "set" in lower):
        payload["green_inferred_from_model_output"] = True
    if payload:
        reject_qa_overreach(payload)
    return {"checked": True, "violations_found": len(payload)}
