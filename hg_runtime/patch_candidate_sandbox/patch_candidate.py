"""Phase 38 patch-candidate representation.

A patch candidate is a *proposed* diff/patch artifact derived from a work
package. It is represented as text + metadata; it is never applied to the live
tree. The candidate hash is deterministic over the redacted patch text.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.proposal_compiler.input_loader import redact_text
from hg_runtime.patch_candidate_sandbox.schemas import (
    PATCH_CANDIDATE_REQUEST_SCHEMA,
    PATCH_CANDIDATE_SCHEMA,
    SANDBOX_ARTIFACT_ONLY,
    UNKNOWN,
    assert_neutral_output,
    neutral_flags,
)


def candidate_hash(patch_text: str) -> str:
    """Deterministic hash over the (redacted) patch text."""
    return canonical_hash({"patch_text": redact_text(patch_text)})


def patch_candidate_request(source: Mapping[str, Any]) -> dict[str, Any]:
    request = {
        "schema": PATCH_CANDIDATE_REQUEST_SCHEMA,
        "source_work_package_id": source["source_work_package_id"],
        "source_work_package_hash": source["source_work_package_hash"],
        "source_status": source["source_status"],
        "eligible_for_patch_candidate": source["eligible_for_patch_candidate"],
        "sandbox_mode": SANDBOX_ARTIFACT_ONLY,
        **neutral_flags(),
    }
    assert_neutral_output(request)
    return request


def build_patch_candidate(
    *,
    source: Mapping[str, Any],
    patch_text: str,
    sandbox_mode: str = SANDBOX_ARTIFACT_ONLY,
    label: str = UNKNOWN,
) -> dict[str, Any]:
    """Represent (never apply) a patch candidate from a READY work package."""
    redacted = redact_text(patch_text or "")
    chash = candidate_hash(patch_text or "")
    candidate = {
        "schema": PATCH_CANDIDATE_SCHEMA,
        "patch_candidate_id": f"pc-{chash.removeprefix('sha256:')[:20]}",
        "label": label,
        "source_work_package_id": source["source_work_package_id"],
        "source_work_package_hash": source["source_work_package_hash"],
        "candidate_hash": chash,
        "sandbox_mode": sandbox_mode,
        "patch_text": redacted,
        "is_representation_only": True,
        **neutral_flags(),
    }
    assert_neutral_output({k: v for k, v in candidate.items() if k != "patch_text"})
    return candidate


__all__ = ["build_patch_candidate", "candidate_hash", "patch_candidate_request"]
