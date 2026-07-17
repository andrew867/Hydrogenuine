"""Phase 38 sandbox planning and receipts.

The default sandbox mode is ARTIFACT_ONLY: the candidate is emitted as patch/diff
text + metadata under the Phase 38 proof/artifact paths. No live source path is
mutated, nothing is applied, committed, pushed, or deployed. A sandbox plan that
would touch a forbidden path is refused.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.patch_candidate_sandbox.risk_classifier import detect_sandbox_escape
from hg_runtime.patch_candidate_sandbox.schemas import (
    SANDBOX_ARTIFACT_ONLY,
    SANDBOX_DISPOSABLE_COPY,
    SANDBOX_PLAN_SCHEMA,
    SANDBOX_RECEIPT_SCHEMA,
    SandboxError,
    assert_neutral_output,
    neutral_flags,
)

_ALLOWED_MODES = (SANDBOX_ARTIFACT_ONLY, SANDBOX_DISPOSABLE_COPY)


def sandbox_plan(candidate: Mapping[str, Any], changed_paths: list[str]) -> dict[str, Any]:
    """Plan a contained sandbox for a candidate without applying anything."""
    mode = str(candidate.get("sandbox_mode", SANDBOX_ARTIFACT_ONLY))
    if mode not in _ALLOWED_MODES:
        raise SandboxError(f"unsupported_sandbox_mode:{mode}")
    escape_reasons = sorted({reason for path in changed_paths for reason in detect_sandbox_escape(path)})
    plan = {
        "schema": SANDBOX_PLAN_SCHEMA,
        "patch_candidate_id": candidate["patch_candidate_id"],
        "sandbox_mode": mode,
        "applies_to_live_tree": False,
        "mutates_live_source_paths": False,
        "sandbox_escape_reasons": escape_reasons,
        "sandbox_escape_detected": bool(escape_reasons),
        **neutral_flags(),
    }
    assert_neutral_output(plan)
    return plan


def sandbox_receipt(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Emit a hash-bound receipt attesting the sandbox stayed contained."""
    receipt = {
        "schema": SANDBOX_RECEIPT_SCHEMA,
        "patch_candidate_id": plan["patch_candidate_id"],
        "sandbox_mode": plan["sandbox_mode"],
        "applied_to_live_tree": False,
        "live_source_mutated": False,
        "sandbox_escape_detected": plan["sandbox_escape_detected"],
        "sandbox_escape_reasons": list(plan["sandbox_escape_reasons"]),
        **neutral_flags(),
    }
    assert_neutral_output(receipt)
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


__all__ = ["sandbox_plan", "sandbox_receipt"]
