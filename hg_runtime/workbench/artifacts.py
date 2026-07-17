"""Artifact receipt helpers for Phase 29."""

from __future__ import annotations

from typing import Any

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.workbench.schemas import ARTIFACT_RECEIPT_SCHEMA, PATCH_CANDIDATE_RECEIPT_SCHEMA, WorkbenchError


def artifact_hash(content: str | bytes) -> str:
    if isinstance(content, bytes):
        payload: dict[str, Any] = {"bytes_hex": content.hex()}
    else:
        payload = {"text": content}
    return canonical_hash(payload)


def draft_artifact_receipt(*, artifact_path: str, content: str, receipt_refs: list[str], patch_candidate: bool = False) -> dict[str, Any]:
    if not receipt_refs:
        raise WorkbenchError("receipt_required:artifact_write")
    digest = artifact_hash(content)
    if not digest:
        raise WorkbenchError("artifact_hash_required")
    receipt = {
        "schema": PATCH_CANDIDATE_RECEIPT_SCHEMA if patch_candidate else ARTIFACT_RECEIPT_SCHEMA,
        "artifact_path": artifact_path,
        "artifact_hash": digest,
        "receipt_refs": receipt_refs,
        "draft_only": True,
        "merged": False,
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "live_side_effects_created": False,
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


__all__ = ["artifact_hash", "draft_artifact_receipt"]
