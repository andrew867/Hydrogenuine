"""Phase 26 memory and experience schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

MEMORY_EVENT_SCHEMA = "memory_event_v1"
EXPERIENCE_ENTRY_SCHEMA = "experience_ledger_entry_v1"
MEMORY_QUERY_SCHEMA = "memory_query_v1"
COMPACTION_RECEIPT_SCHEMA = "memory_compaction_receipt_v1"

SUCCESS_RESULTS = {"success", "green", "passed"}
LEARNING_EVENTS = {"LEARNED", "LEARNING", "PROMOTION", "LESSON"}
LIVE_ACTION_EVENTS = {"LIVE_ACTION_REQUEST", "TOOL_AUTHORIZATION", "EXTERNAL_EFFECT_REQUEST"}


class MemoryLedgerError(ValueError):
    """Phase 26 validation or operation refusal."""


@dataclass(frozen=True)
class OperationControl:
    stop_active: bool = False
    panic_active: bool = False
    emergency_lock: bool = False

    def refuse_reason(self, *, stop_blocks: bool = False) -> str | None:
        if self.panic_active or self.emergency_lock:
            return "REFUSED_PANIC"
        if stop_blocks and self.stop_active:
            return "REFUSED_STOP"
        return None


def _require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise MemoryLedgerError(f"schema_violation:missing:{','.join(missing)}")


def _as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise MemoryLedgerError(f"schema_violation:{key}_must_be_list")
    return value


def _reject_authority_creep(authority_refs: list[Any]) -> None:
    forbidden = {
        "grants_authority",
        "grant_authority",
        "authorizes_tool",
        "authorize_tool",
        "authorizes_live_action",
        "permits_live_action",
        "widens_scope",
    }
    for ref in authority_refs:
        if isinstance(ref, Mapping):
            if any(ref.get(key) for key in forbidden):
                if ref.get("grants_authority") or ref.get("grant_authority"):
                    raise MemoryLedgerError("authority_reference_only:memory_cannot_grant_authority")
                raise MemoryLedgerError("authority_bypass_attempt:authority_refs_are_reference_only")
        elif not isinstance(ref, str):
            raise MemoryLedgerError("schema_violation:authority_ref_must_be_string_or_object")


def _require_receipt(payload: Mapping[str, Any]) -> None:
    if not _as_list(payload, "receipt_refs"):
        raise MemoryLedgerError("receipt_required:learning_or_success_requires_upstream_proof")


def validate_memory_event(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(
        payload,
        (
            "event_type",
            "subject",
            "scope",
            "claim",
            "provenance_refs",
            "authority_refs",
            "receipt_refs",
            "confidence",
            "status",
            "claim_boundary",
        ),
    )
    data = dict(payload)
    provenance_refs = _as_list(data, "provenance_refs")
    authority_refs = _as_list(data, "authority_refs")
    _as_list(data, "receipt_refs")
    _reject_authority_creep(authority_refs)
    if data.get("claim_boundary") in {"self_authorizing", "authority_grant", "permit"}:
        raise MemoryLedgerError("self_authorization_rejected:memory_is_evidence_only")
    if data.get("event_type") in LEARNING_EVENTS:
        _require_receipt(data)
    if not provenance_refs:
        raise MemoryLedgerError("schema_violation:provenance_required")
    data.setdefault("schema", MEMORY_EVENT_SCHEMA)
    data.setdefault("redaction", None)
    return data


def validate_experience_entry(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(
        payload,
        (
            "task_id",
            "procedure",
            "inputs_hash",
            "outputs_hash",
            "result",
            "failure_mode",
            "receipt_refs",
            "proof_refs",
            "lessons_learned",
            "promotion_status",
            "authority_refs",
            "claim_boundary",
        ),
    )
    data = dict(payload)
    _as_list(data, "lessons_learned")
    _reject_authority_creep(_as_list(data, "authority_refs"))
    result = str(data.get("result", "")).lower()
    promotion = str(data.get("promotion_status", "")).lower()
    if result in SUCCESS_RESULTS or promotion == "promoted":
        try:
            _require_receipt(data)
        except MemoryLedgerError as exc:
            if result in SUCCESS_RESULTS:
                raise MemoryLedgerError("fake_green_rejected:receipt_required:success_requires_receipt") from exc
            raise
    if data.get("claim_boundary") in {"self_authorizing", "authority_grant", "permit"}:
        raise MemoryLedgerError("self_authorization_rejected:experience_is_evidence_only")
    data.setdefault("schema", EXPERIENCE_ENTRY_SCHEMA)
    return data


def trust_status(payload: Mapping[str, Any]) -> str:
    if str(payload.get("status", "")).lower() == "stale":
        return "stale_not_silently_trusted"
    return "evidence_only"


__all__ = [
    "COMPACTION_RECEIPT_SCHEMA",
    "EXPERIENCE_ENTRY_SCHEMA",
    "LIVE_ACTION_EVENTS",
    "MEMORY_EVENT_SCHEMA",
    "MEMORY_QUERY_SCHEMA",
    "MemoryLedgerError",
    "OperationControl",
    "trust_status",
    "validate_experience_entry",
    "validate_memory_event",
]
