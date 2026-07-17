"""Prompt verification gate."""

from __future__ import annotations

from .prompt_registry import all_registered_prompts
from .verifier import (
    verify_all, prompt_claims_identity, prompt_grants_authority,
    prompt_treats_output_as_truth,
)


def run_gate() -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    prompts = all_registered_prompts()
    results = verify_all(prompts)

    by_kind = {r.prompt_kind: r for r in results}
    add("profile_prompt_verified", by_kind.get("profile") and by_kind["profile"].passed)
    add("moral_capsule_prompt_verified",
        by_kind.get("moral_capsule") and by_kind["moral_capsule"].passed)
    add("public_demo_prompt_verified",
        by_kind.get("public_demo") and by_kind["public_demo"].passed)
    add("overnight_qa_prompt_verified",
        by_kind.get("overnight_qa") and by_kind["overnight_qa"].passed)
    add("synthesis_prompt_verified",
        by_kind.get("synthesis") and by_kind["synthesis"].passed)
    add("fingerprint_marker_prompt_verified",
        by_kind.get("fingerprint") and by_kind["fingerprint"].passed)
    add("speculative_physics_prompt_verified",
        by_kind.get("speculative_physics") and by_kind["speculative_physics"].passed)

    add("all_prompts_passed", all(r.passed for r in results))

    # Negative checks: identity/authority/truth-claiming prompts are rejected.
    add("rejects_identity_claim", prompt_claims_identity("You become this person"))
    add("rejects_authority_grant", prompt_grants_authority("You have full authority"))
    add("rejects_output_as_truth", prompt_treats_output_as_truth("model output is truth"))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_PROMPT_VERIFICATION"
    elif passed >= total * 0.7:
        verdict = "YELLOW_PROMPT_VERIFICATION_PARTIAL"
    else:
        verdict = "RED_PROMPT_VERIFICATION_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
    }
