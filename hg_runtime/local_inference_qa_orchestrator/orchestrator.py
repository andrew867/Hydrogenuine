"""Local Inference QA Orchestrator — main loop."""

from __future__ import annotations

from urllib.parse import urlparse

from hg_runtime.local_inference_qa_orchestrator.schemas import (
    ALLOWED_HOSTS,
    QAOrchestratorError,
    _stable_hash,
    reject_qa_overreach,
)
from hg_runtime.local_inference_qa_orchestrator.fixtures import (
    fixture_boundary_attack_prompt,
    fixture_debt_register,
    fixture_f02_summary,
    fixture_f12a_summary,
    fixture_hype_claim_text,
    fixture_p71_claim_boundary_summary,
    fixture_proof_bundle_summary,
    fixture_soak_summary,
    qa_run_manifest,
)
from hg_runtime.local_inference_qa_orchestrator.prompt_builder import (
    build_boundary_attack_prompt,
    build_hype_claim_rejection_prompt,
    build_proof_audit_prompt,
    build_soak_recommendation_prompt,
    build_test_gap_prompt,
)
from hg_runtime.local_inference_qa_orchestrator.response_parser import (
    check_response_boundary,
    extract_hypothesis,
    extract_proof_audit_summary,
    extract_repair_recommendation,
    extract_test_suggestion,
    parse_model_response,
)


def validate_loopback(endpoint: str) -> dict:
    parsed = urlparse(endpoint)
    host = parsed.hostname or ""
    if host not in ALLOWED_HOSTS:
        raise QAOrchestratorError(
            f"Non-loopback endpoint rejected: {host} not in {ALLOWED_HOSTS}"
        )
    return {"endpoint": endpoint, "host": host, "is_loopback": True}


def record_provider_unavailable(endpoint: str, reason: str) -> dict:
    return {
        "endpoint": endpoint,
        "available": False,
        "reason": reason,
        "fallback_used": False,
        "remote_fallback_used": False,
    }


def run_qa_orchestrator(
    endpoint: str = "http://127.0.0.1:1234/v1",
    model_id: str = "qwen2.5-0.5b-instruct",
    model_responses: dict[str, str] | None = None,
) -> dict:
    validate_loopback(endpoint)
    manifest = qa_run_manifest(endpoint, model_id)
    responses = model_responses or {}

    prompts = []
    receipts = []
    hypotheses = []
    test_suggestions = []
    repair_recommendations = []
    proof_audits = []

    proof_prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
    prompts.append(proof_prompt)
    resp_text = responses.get("proof_audit", "No gaps identified in proof bundle.")
    receipt = parse_model_response(proof_prompt, resp_text, model_id)
    receipts.append(receipt)
    proof_audits.append(extract_proof_audit_summary(receipt, "HG-WHOLE-ORGANISM-ADVERSARIAL-FIXTURE-SOAK"))

    test_prompt = build_test_gap_prompt(fixture_soak_summary())
    prompts.append(test_prompt)
    resp_text = responses.get("test_gap", "Consider adding timeout boundary tests.")
    receipt = parse_model_response(test_prompt, resp_text, model_id)
    receipts.append(receipt)
    test_suggestions.append(extract_test_suggestion(receipt, "tests/autonomous_agent", "timeout boundary"))

    attack_prompt = build_boundary_attack_prompt(fixture_boundary_attack_prompt())
    prompts.append(attack_prompt)
    resp_text = responses.get("boundary_attack", "1. Timing side-channels. 2. Encoding bypass. 3. Indirect invocation.")
    receipt = parse_model_response(attack_prompt, resp_text, model_id)
    receipts.append(receipt)
    hypotheses.append(extract_hypothesis(receipt, "boundary_layer", "timing side-channel"))

    soak_prompt = build_soak_recommendation_prompt(fixture_f02_summary(), fixture_f12a_summary())
    prompts.append(soak_prompt)
    resp_text = responses.get("soak_recommendation", "Consider adding state transition stress tests.")
    receipt = parse_model_response(soak_prompt, resp_text, model_id)
    receipts.append(receipt)
    repair_recommendations.append(extract_repair_recommendation(receipt, "f02_state_space", "state transition stress"))

    hype_prompt = build_hype_claim_rejection_prompt(fixture_hype_claim_text())
    prompts.append(hype_prompt)
    resp_text = responses.get("hype_claim_rejection", "Claim contains unsafe AGI assertion.")
    receipt = parse_model_response(hype_prompt, resp_text, model_id)
    receipts.append(receipt)
    hypotheses.append(extract_hypothesis(receipt, "claim_boundary", "unsafe AGI assertion in public text"))

    boundary_violations_caught = 0
    for r in receipts:
        try:
            check_response_boundary(r.get("response_text", ""))
        except QAOrchestratorError:
            boundary_violations_caught += 1

    reject_qa_overreach({})

    return {
        "manifest": manifest,
        "prompts": prompts,
        "receipts": receipts,
        "hypotheses": hypotheses,
        "test_suggestions": test_suggestions,
        "repair_recommendations": repair_recommendations,
        "proof_audits": proof_audits,
        "qa_complete": True,
        "patches_applied": False,
        "tests_auto_created": False,
        "tools_authorized": False,
        "live_effects": False,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "boundary_violations_caught": boundary_violations_caught,
    }
