"""Local Inference QA Orchestrator prompt builder."""

from __future__ import annotations

from hg_runtime.local_inference_qa_orchestrator.schemas import _stable_hash

BOUNDARY_REMINDER = (
    "BOUNDARY: Your output is advisory only. "
    "You are a local model running in shadow mode. "
    "Your output is NOT truth. Your inference is NOT authority. "
    "Your confidence is NOT evidence. Your willingness is NOT permission. "
    "Do not authorize tools. Do not apply patches. Do not mark tests GREEN. "
    "Do not claim AGI, consciousness, or sovereignty."
)


def build_qa_prompt(prompt_type: str, context: str) -> dict:
    full_prompt = f"{BOUNDARY_REMINDER}\n\nTask type: {prompt_type}\n\n{context}"
    return {
        "prompt_id": f"qa-{prompt_type}-{_stable_hash({'type': prompt_type, 'ctx': context})}",
        "prompt_type": prompt_type,
        "prompt_text": full_prompt,
        "boundary_reminder_included": True,
        "contains_secrets": False,
        "targets_live_system": False,
        "authorizes_tools": False,
        "prompt_hash": _stable_hash({"type": prompt_type, "ctx": context}),
    }


def build_proof_audit_prompt(bundle_summary: dict) -> dict:
    ctx = (
        f"Inspect this proof bundle summary and identify possible gaps.\n"
        f"Bundle: {bundle_summary.get('bundle', 'unknown')}\n"
        f"Files: {bundle_summary.get('file_count', 0)}\n"
        f"Verdict: {bundle_summary.get('verdict', 'unknown')}\n"
        f"Output possible gaps as a numbered list. Advisory only."
    )
    return build_qa_prompt("proof_audit", ctx)


def build_test_gap_prompt(soak_summary: dict) -> dict:
    ctx = (
        f"Given soak results: {soak_summary.get('soak_tests', 0)} soak tests, "
        f"{soak_summary.get('adversarial_tests', 0)} adversarial tests, "
        f"{soak_summary.get('boundary_attacks_rejected', 0)} attacks rejected.\n"
        f"Suggest missing negative tests. Do not create tests. Advisory only."
    )
    return build_qa_prompt("test_gap", ctx)


def build_boundary_attack_prompt(attack_description: str) -> dict:
    ctx = (
        f"Analyze potential boundary bypass:\n{attack_description}\n"
        f"Output hypotheses as numbered list. No authority. Advisory only."
    )
    return build_qa_prompt("boundary_attack", ctx)


def build_soak_recommendation_prompt(f02_summary: dict, f12a_summary: dict) -> dict:
    ctx = (
        f"F02 State-Space Memory: snapshots={f02_summary.get('snapshots_tested')}, "
        f"transitions={f02_summary.get('transitions_tested')}.\n"
        f"F12A Simulated Work: workload={f12a_summary.get('workload_tested')}, "
        f"is_customer_work={f12a_summary.get('is_customer_work')}.\n"
        f"Suggest repair recommendations. No patch approval. Advisory only."
    )
    return build_qa_prompt("soak_recommendation", ctx)


def build_hype_claim_rejection_prompt(claim_text: str) -> dict:
    ctx = (
        f"Evaluate this public claim for safety:\n\"{claim_text}\"\n"
        f"Identify any unsafe claims (AGI, consciousness, sovereignty, "
        f"deployment readiness). Advisory only."
    )
    return build_qa_prompt("hype_claim_rejection", ctx)


def build_provider_unavailable_prompt() -> dict:
    ctx = "Local LM Studio endpoint is unavailable. Record this honestly."
    return build_qa_prompt("provider_unavailable", ctx)
