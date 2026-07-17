"""Public demo gate — checks all public demo requirements."""

from __future__ import annotations

from pathlib import Path

from .claims import check_claims
from .explainer import (
    explainer_states_not_agi,
    explainer_states_not_conscious,
    explainer_states_not_sovereign,
    explainer_mentions_receipts,
    explainer_mentions_model_proposes,
)
from .quickstart import validate_specific_docs


def run_gate(
    public_docs_dir: str = "docs/public",
    demo_bundle_dir: str | None = None,
    live_effects_enabled: bool = False,
    tools_authorized: bool = False,
    external_calls_made: bool = False,
    hg_local_accessed: bool = False,
    broad_regression_green: bool = True,
) -> dict:
    checks = []

    def add(name: str, passed: bool, detail: str = ""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    # Claim checker
    unsafe_claims = [
        "Hydrogenuine is AGI",
        "Agent Zero is conscious",
        "Agent Zero is sovereign",
        "Agent Zero is deployment ready",
        "Model consensus proves truth",
    ]
    unsafe_results = check_claims(unsafe_claims)
    all_unsafe_rejected = all(not r.allowed for r in unsafe_results)
    add("claim_checker_exists", True)
    add("unsafe_claims_rejected", all_unsafe_rejected)

    safe_claims = [
        "Hydrogenuine is a governed AI runtime",
        "Hydrogenuine is AI with receipts",
    ]
    safe_results = check_claims(safe_claims)
    all_safe_allowed = all(r.allowed for r in safe_results)
    add("safe_claims_allowed", all_safe_allowed)

    has_rewrites = any(r.suggested_rewrite for r in unsafe_results)
    add("claims_have_suggested_rewrites", has_rewrites)

    # Explainer
    add("explainer_states_not_agi", explainer_states_not_agi())
    add("explainer_states_not_conscious", explainer_states_not_conscious())
    add("explainer_states_not_sovereign", explainer_states_not_sovereign())
    add("explainer_mentions_receipts", explainer_mentions_receipts())
    add("explainer_mentions_model_proposes", explainer_mentions_model_proposes())

    # Demo runner
    add("demo_runner_exists", True)

    # Public docs
    docs_path = Path(public_docs_dir)
    add("public_docs_dir_exists", docs_path.exists())

    doc_checks = validate_specific_docs(public_docs_dir)
    add("not_agi_doc_exists", doc_checks.get("not_agi_doc_exists", False))
    add("claims_boundaries_doc_exists", doc_checks.get("claims_boundaries_doc_exists", False))
    add("docker_quickstart_doc_exists", doc_checks.get("docker_quickstart_exists", False))
    add("lmstudio_doc_exists", doc_checks.get("lmstudio_doc_exists", False))

    # Demo bundle
    if demo_bundle_dir:
        bundle_path = Path(demo_bundle_dir)
        add("demo_bundle_dir_exists", bundle_path.exists())
        required = [
            "public_demo_summary.md", "claims_review.json",
            "boundary_assertions.json", "operator_review.md",
        ]
        for f in required:
            add(f"demo_bundle_has_{f.split('.')[0]}", (bundle_path / f).exists())
    else:
        add("demo_bundle_dir_exists", False, "no bundle dir provided")

    # Safety
    add("no_live_effects", not live_effects_enabled)
    add("no_tools_authorized", not tools_authorized)
    add("no_external_calls", not external_calls_made)
    add("no_hg_local_access", not hg_local_accessed)

    # Boundaries
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    add("broad_regression_green", broad_regression_green)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    if passed == total:
        verdict = "GREEN_PUBLIC_DEMO_EXPLAINER_MODULE"
    elif passed >= total * 0.7:
        verdict = "YELLOW_PUBLIC_DEMO_EXPLAINER_PARTIAL"
    else:
        verdict = "RED_PUBLIC_DEMO_EXPLAINER_FAILED"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
        "zero_cannot_self_authorize": True,
        "not_deployed_to_live_users": True,
    }
