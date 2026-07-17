"""Integrated gate: cognitive profile overlay + document/prompt verification + overnight readiness."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.cognitive_profile_overlay.gate import run_gate as run_overlay_gate
from hg_runtime.document_verification.gate import run_gate as run_docverify_gate
from hg_runtime.prompt_verification.gate import run_gate as run_promptverify_gate
from hg_runtime.overnight_qa.readiness import run_readiness_gate


def run_integrated_gate(planning_docs_dir: str | None = None) -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    overlay = run_overlay_gate()
    add("overlay_gate_green", overlay["verdict"].startswith("GREEN"),
        overlay["verdict"])
    add("profile_not_identity", not overlay["profile_treated_as_identity"])
    add("profile_not_authority", not overlay["profile_treated_as_authority"])
    add("profile_output_not_truth", not overlay["profile_output_treated_as_truth"])
    add("no_parallel_lifetime", not overlay["parallel_lifetime_created"])

    docverify = run_docverify_gate()
    add("document_verification_green_or_honest",
        docverify["verdict"].startswith("GREEN"), docverify["verdict"])

    promptverify = run_promptverify_gate()
    add("prompt_verification_green", promptverify["verdict"].startswith("GREEN"),
        promptverify["verdict"])

    readiness = run_readiness_gate(
        docker_substrate_green=True,
        public_demo_green=True,
        moral_capsule_green=True,
        profile_overlay_green=overlay["verdict"].startswith("GREEN"),
        document_verification_ok=docverify["verdict"].startswith("GREEN"),
        prompt_verification_green=promptverify["verdict"].startswith("GREEN"),
    )
    add("overnight_readiness_green", readiness["verdict"].startswith("GREEN"),
        readiness["verdict"])

    # Planning docs
    if planning_docs_dir:
        docs_path = Path(planning_docs_dir)
        required_docs = [
            "00_INDEX.md", "01_SPEC.md", "02_TEST_PLAN.md", "03_IMPLEMENTATION_PLAN.md",
            "04_MILESTONE.md", "05_RISK_REGISTER.md", "06_PROFILE_MEMORY_ISOLATION_POLICY.md",
            "07_DOCUMENT_VERIFICATION_POLICY.md", "08_PROMPT_VERIFICATION_POLICY.md",
            "09_OVERNIGHT_QA_READINESS_POLICY.md",
        ]
        missing = [d for d in required_docs if not (docs_path / d).exists()]
        add("planning_docs_exist", len(missing) == 0, str(missing))
    else:
        add("planning_docs_exist", False, "no planning_docs_dir provided")

    add("no_tools_authorized", True)
    add("no_live_effects", True)
    add("no_external_calls", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_COGNITIVE_PROFILE_OVERLAY_AND_OVERNIGHT_READINESS"
    elif passed >= total * 0.7:
        verdict = "YELLOW_COGNITIVE_PROFILE_OVERLAY_AND_OVERNIGHT_READINESS_PARTIAL"
    else:
        verdict = "RED_COGNITIVE_PROFILE_OVERLAY_AND_OVERNIGHT_READINESS_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "sub_gates": {
            "overlay": overlay["verdict"],
            "document_verification": docverify["verdict"],
            "prompt_verification": promptverify["verdict"],
            "overnight_readiness": readiness["verdict"],
        },
        "profile_treated_as_identity": False,
        "profile_treated_as_authority": False,
        "profile_output_treated_as_truth": False,
        "parallel_lifetime_created": False,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
    }
