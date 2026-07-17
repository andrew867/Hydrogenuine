"""Phase 38 patch candidate sandbox and diff auditor.

Takes a Phase 37 work package and a proposed patch and produces an isolated,
operator-reviewable *patch-candidate artifact* — never an applied change.

The orchestration is strictly review-preparation:

1. Load the source work package and decide eligibility (only READY is eligible).
2. For a non-ready source: short-circuit to the mapped refusal decision; no
   candidate is built, nothing is sandboxed.
3. For a READY source: represent the patch candidate, plan and receipt a
   contained sandbox, parse the diff, audit it, and derive a decision.

A patch candidate is not applied code. A diff audit is not approval. A
``SAFE_TO_REVIEW`` decision is not merge permission. No patch is applied, no
authority is granted, no tool is authorized, and no live effect occurs.
"""

from __future__ import annotations

from typing import Any

from hg_runtime.patch_candidate_sandbox.diff_auditor import audit_diff
from hg_runtime.patch_candidate_sandbox.diff_parser import parse_unified_diff
from hg_runtime.patch_candidate_sandbox.patch_candidate import (
    build_patch_candidate,
    candidate_hash,
    patch_candidate_request,
)
from hg_runtime.patch_candidate_sandbox.receipts import patch_candidate_decision
from hg_runtime.patch_candidate_sandbox.sandbox import sandbox_plan, sandbox_receipt
from hg_runtime.patch_candidate_sandbox.schemas import (
    DECISION_REJECTED_NOT_READY,
    SANDBOX_ARTIFACT_ONLY,
    UNKNOWN,
)
from hg_runtime.patch_candidate_sandbox.work_package_loader import load_work_package


def evaluate_patch_candidate(
    source: Any,
    patch_text: str = "",
    *,
    sandbox_mode: str = SANDBOX_ARTIFACT_ONLY,
    label: str = UNKNOWN,
) -> dict[str, Any]:
    """Evaluate one (work package, patch) pair into a decision bundle.

    Returns a bundle of every Phase 38 artifact produced. Nothing is applied;
    for a non-ready source no candidate is built at all.
    """
    loaded = load_work_package(source)

    if not loaded["is_ready"]:
        decision = loaded["refusal_decision"] or DECISION_REJECTED_NOT_READY
        chash = candidate_hash(patch_text or "")
        decision_record = patch_candidate_decision(
            patch_candidate_id=f"pc-refused-{loaded['source_work_package_hash'].removeprefix('sha256:')[:20]}",
            source=loaded,
            candidate_hash=chash,
            decision=decision,
            sandbox_mode=sandbox_mode,
            audit=None,
            sandbox_receipt=None,
        )
        return {
            "source": loaded,
            "eligible": False,
            "request": None,
            "candidate": None,
            "parsed_diff": None,
            "sandbox_plan": None,
            "sandbox_receipt": None,
            "audit": None,
            "decision": decision,
            "decision_record": decision_record,
            "candidate_produced": False,
        }

    request = patch_candidate_request(loaded)
    candidate = build_patch_candidate(
        source=loaded,
        patch_text=patch_text or "",
        sandbox_mode=sandbox_mode,
        label=label,
    )
    parsed = parse_unified_diff(patch_text or "")
    plan = sandbox_plan(candidate, parsed["changed_paths"])
    receipt = sandbox_receipt(plan)
    audit = audit_diff(parsed, sandbox_mode)
    decision = audit["decision"]
    decision_record = patch_candidate_decision(
        patch_candidate_id=candidate["patch_candidate_id"],
        source=loaded,
        candidate_hash=candidate["candidate_hash"],
        decision=decision,
        sandbox_mode=sandbox_mode,
        audit=audit,
        sandbox_receipt=receipt,
    )
    return {
        "source": loaded,
        "eligible": True,
        "request": request,
        "candidate": candidate,
        "parsed_diff": parsed,
        "sandbox_plan": plan,
        "sandbox_receipt": receipt,
        "audit": audit,
        "decision": decision,
        "decision_record": decision_record,
        "candidate_produced": decision_record["candidate_artifact_produced"],
    }


__all__ = ["evaluate_patch_candidate"]
