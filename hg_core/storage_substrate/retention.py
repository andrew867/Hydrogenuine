"""Retention, compaction, and archive planning — non-destructive."""

from __future__ import annotations

from typing import Any

from hg_core.storage_substrate.common import authority_fields, stable_hash, utc_now_iso

RETENTION_CLASSES = {
    "PROOF_BUNDLE": "NEVER_PRUNE",
    "COMMAND_LOG": "NEVER_PRUNE",
    "AUTHORITY_CHAIN": "NEVER_PRUNE",
    "EVENT_LOG": "AUDIT_RETENTION",
    "STRUCTURED_RECORD": "AUDIT_RETENTION",
    "PROOF_INDEX": "AUDIT_RETENTION",
    "VECTOR_MEMORY": "COMPACTABLE",
    "EMBEDDING_RECORD": "COMPACTABLE",
    "MODEL_CACHE": "CACHE",
    "TEMP_CACHE": "CACHE",
    "SECRET_OR_CREDENTIAL": "SECRET_REF_ONLY",
}

ALL_RETENTION_CLASSES = frozenset({
    "NEVER_PRUNE",
    "AUDIT_RETENTION",
    "COMPACTABLE",
    "CACHE",
    "SECRET_REF_ONLY",
    "UNKNOWN_REVIEW_REQUIRED",
})


class RetentionPlanner:
    def __init__(self) -> None:
        self._receipts: list[dict[str, Any]] = []

    def classify(self, storage_class: str) -> str:
        return RETENTION_CLASSES.get(storage_class, "UNKNOWN_REVIEW_REQUIRED")

    def dry_run_compaction(self, target_ref: str, storage_class: str) -> dict[str, Any]:
        retention_class = self.classify(storage_class)
        plan = {
            "target_ref": target_ref,
            "storage_class": storage_class,
            "retention_class": retention_class,
            "dry_run": True,
            "destructive_action_taken": False,
            "requires_review": retention_class in {"NEVER_PRUNE", "SECRET_REF_ONLY", "UNKNOWN_REVIEW_REQUIRED"},
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        plan["hash"] = stable_hash(plan)
        self._receipts.append(plan)
        return plan

    def refuse_destructive_delete(self, target_ref: str) -> dict[str, Any]:
        return {
            "target_ref": target_ref,
            "delete_refused": True,
            "reason": "destructive_deletion_requires_explicit_operator_approval",
            "operator_approved": False,
            **authority_fields(),
        }

    def verify_proof_not_prunable(self, target_ref: str, active_authority_refs: list[str]) -> dict[str, Any]:
        is_active = target_ref in active_authority_refs
        return {
            "target_ref": target_ref,
            "is_active_authority_proof": is_active,
            "prunable": False if is_active else None,
            "reason": "active_proof_cannot_be_pruned" if is_active else "not_in_active_authority_chain",
            **authority_fields(),
        }

    def compaction_receipts(self) -> list[dict[str, Any]]:
        return list(self._receipts)
