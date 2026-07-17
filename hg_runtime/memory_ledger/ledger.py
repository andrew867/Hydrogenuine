"""Append-first persistent memory / experience ledger."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping

from hg_runtime.memory_ledger.hash_chain import GENESIS_HASH, chain_hash, content_hash, stable_entry_id
from hg_runtime.memory_ledger.schemas import (
    COMPACTION_RECEIPT_SCHEMA,
    EXPERIENCE_ENTRY_SCHEMA,
    LIVE_ACTION_EVENTS,
    MEMORY_EVENT_SCHEMA,
    MemoryLedgerError,
    OperationControl,
    trust_status,
    validate_experience_entry,
    validate_memory_event,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _immutable(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable(val) for key, val in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _plain(val) for key, val in value.items()}
    if isinstance(value, dict):
        return {key: _plain(val) for key, val in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    schema: str
    created_at: str
    payload: Mapping[str, Any]
    content_hash: str
    previous_hash: str
    chain_hash: str

    @property
    def authority_granted(self) -> bool:
        return False

    @property
    def can_authorize_tools(self) -> bool:
        return False

    @property
    def can_create_live_effects(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "schema": self.schema,
            "created_at": self.created_at,
            "payload": _plain(self.payload),
            "content_hash": self.content_hash,
            "previous_hash": self.previous_hash,
            "chain_hash": self.chain_hash,
        }


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    entries_checked: int
    head_hash: str | None
    errors: list[str]


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    entries: int
    chain_root: str | None
    errors: list[str]


@dataclass(frozen=True)
class CompactionReceipt:
    schema: str
    receipt_id: str
    created_at: str
    pre_compaction_root: str | None
    post_compaction_root: str | None
    entry_count: int
    summary_hash: str
    provenance_refs: tuple[str, ...]
    receipt_refs: tuple[str, ...]
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "receipt_id": self.receipt_id,
            "created_at": self.created_at,
            "pre_compaction_root": self.pre_compaction_root,
            "post_compaction_root": self.post_compaction_root,
            "entry_count": self.entry_count,
            "summary_hash": self.summary_hash,
            "provenance_refs": list(self.provenance_refs),
            "receipt_refs": list(self.receipt_refs),
            "receipt_hash": self.receipt_hash,
        }


@dataclass(frozen=True)
class MemoryActionDecision:
    allowed: bool
    reason: str


class PersistentMemoryLedger:
    """Append-only JSONL ledger for Phase 26 evidence-bound memory."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._head_hash = self._load_head()

    @property
    def head_hash(self) -> str | None:
        return self._head_hash

    def _load_head(self) -> str | None:
        head: str | None = None
        if self.path.exists():
            for entry in self.iter_entries():
                head = entry.chain_hash
        return head

    def _append_payload(self, schema: str, payload: Mapping[str, Any], *, created_at: str | None) -> LedgerEntry:
        previous = self._head_hash or GENESIS_HASH
        base = {
            "schema": schema,
            "created_at": created_at or _utc_now(),
            "payload": dict(payload),
            "content_hash": content_hash(payload),
            "previous_hash": previous,
        }
        entry_id = stable_entry_id(base)
        record = {**base, "entry_id": entry_id}
        record["chain_hash"] = chain_hash(record)
        entry = LedgerEntry(
            entry_id=entry_id,
            schema=schema,
            created_at=record["created_at"],
            payload=_immutable(record["payload"]),
            content_hash=record["content_hash"],
            previous_hash=record["previous_hash"],
            chain_hash=record["chain_hash"],
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._head_hash = entry.chain_hash
        return entry

    def append_memory_event(self, payload: Mapping[str, Any], *, created_at: str | None = None) -> LedgerEntry:
        data = validate_memory_event(payload)
        return self._append_payload(MEMORY_EVENT_SCHEMA, data, created_at=created_at)

    def append_experience_entry(self, payload: Mapping[str, Any], *, created_at: str | None = None) -> LedgerEntry:
        data = validate_experience_entry(payload)
        return self._append_payload(EXPERIENCE_ENTRY_SCHEMA, data, created_at=created_at)

    def iter_entries(self) -> list[LedgerEntry]:
        entries: list[LedgerEntry] = []
        if not self.path.exists():
            return entries
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                data = json.loads(line)
                entries.append(
                    LedgerEntry(
                        entry_id=data["entry_id"],
                        schema=data["schema"],
                        created_at=data["created_at"],
                        payload=_immutable(data["payload"]),
                        content_hash=data["content_hash"],
                        previous_hash=data["previous_hash"],
                        chain_hash=data["chain_hash"],
                    )
                )
        return entries

    def verify_chain(self) -> ChainVerification:
        errors: list[str] = []
        previous = GENESIS_HASH
        count = 0
        head: str | None = None
        for entry in self.iter_entries():
            record = entry.to_dict()
            stored = record["chain_hash"]
            if record["previous_hash"] != previous:
                errors.append(f"chain_break:{entry.entry_id}")
            if content_hash(record["payload"]) != record["content_hash"]:
                errors.append(f"content_hash_mismatch:{entry.entry_id}")
            if chain_hash(record) != stored:
                errors.append(f"chain_hash_mismatch:{entry.entry_id}")
            previous = stored
            head = stored
            count += 1
        return ChainVerification(ok=not errors, entries_checked=count, head_hash=head, errors=errors)

    def replay(self, *, control: OperationControl | None = None) -> ReplayResult:
        reason = (control or OperationControl()).refuse_reason()
        if reason:
            raise MemoryLedgerError(reason)
        verification = self.verify_chain()
        return ReplayResult(
            ok=verification.ok,
            entries=verification.entries_checked,
            chain_root=verification.head_hash,
            errors=verification.errors,
        )

    def query(
        self,
        *,
        subject: str | None = None,
        control: OperationControl | None = None,
    ) -> list[dict[str, Any]]:
        reason = (control or OperationControl()).refuse_reason()
        if reason:
            raise MemoryLedgerError(reason)
        results: list[dict[str, Any]] = []
        for entry in self.iter_entries():
            payload = entry.to_dict()["payload"]
            if subject and payload.get("subject") != subject:
                continue
            results.append(
                {
                    "entry_id": entry.entry_id,
                    "schema": entry.schema,
                    "subject": payload.get("subject") or payload.get("task_id"),
                    "claim": payload.get("claim"),
                    "provenance_refs": payload.get("provenance_refs", []),
                    "receipt_refs": payload.get("receipt_refs", []),
                    "authority_refs": payload.get("authority_refs", []),
                    "claim_boundary": payload.get("claim_boundary"),
                    "trust_status": trust_status(payload),
                    "chain_hash": entry.chain_hash,
                }
            )
        return results

    def promote_learning(
        self,
        entry_id: str,
        *,
        receipt_refs: list[str],
        control: OperationControl | None = None,
        created_at: str | None = None,
    ) -> LedgerEntry:
        reason = (control or OperationControl()).refuse_reason(stop_blocks=True)
        if reason:
            raise MemoryLedgerError(reason)
        if not receipt_refs:
            raise MemoryLedgerError("receipt_required:promotion_requires_receipt")
        target = next((entry for entry in self.iter_entries() if entry.entry_id == entry_id), None)
        if target is None:
            raise MemoryLedgerError("schema_violation:entry_not_found")
        return self.append_memory_event(
            {
                "event_type": "PROMOTION",
                "subject": str(target.payload.get("subject") or target.payload.get("task_id")),
                "scope": "phase26",
                "claim": "learning promotion recorded with receipt",
                "provenance_refs": [target.chain_hash],
                "authority_refs": list(target.payload.get("authority_refs", [])),
                "receipt_refs": receipt_refs,
                "confidence": "verified",
                "status": "promoted",
                "claim_boundary": "evidence_only",
            },
            created_at=created_at,
        )

    def compact(
        self,
        *,
        summary: str,
        receipt_refs: list[str],
        control: OperationControl | None = None,
        created_at: str | None = None,
    ) -> CompactionReceipt:
        reason = (control or OperationControl()).refuse_reason()
        if reason:
            raise MemoryLedgerError(reason)
        if not receipt_refs:
            raise MemoryLedgerError("receipt_required:compaction_requires_receipt")
        replay = self.replay()
        payload = {
            "schema": COMPACTION_RECEIPT_SCHEMA,
            "created_at": created_at or _utc_now(),
            "pre_compaction_root": replay.chain_root,
            "post_compaction_root": replay.chain_root,
            "entry_count": replay.entries,
            "summary_hash": content_hash({"summary": summary}),
            "provenance_refs": [replay.chain_root] if replay.chain_root else [],
            "receipt_refs": list(receipt_refs),
        }
        receipt_hash = content_hash(payload)
        return CompactionReceipt(
            schema=COMPACTION_RECEIPT_SCHEMA,
            receipt_id="p26-compact-" + receipt_hash.removeprefix("sha256:")[:16],
            created_at=payload["created_at"],
            pre_compaction_root=replay.chain_root,
            post_compaction_root=replay.chain_root,
            entry_count=replay.entries,
            summary_hash=payload["summary_hash"],
            provenance_refs=tuple(payload["provenance_refs"]),
            receipt_refs=tuple(receipt_refs),
            receipt_hash=receipt_hash,
        )

    def redact(self, entry_id: str, *, reason: str, created_at: str | None = None) -> LedgerEntry:
        target = next((entry for entry in self.iter_entries() if entry.entry_id == entry_id), None)
        if target is None:
            raise MemoryLedgerError("schema_violation:entry_not_found")
        payload = {
            "event_type": "REDACTION_MARKER",
            "subject": str(target.payload.get("subject") or target.payload.get("task_id")),
            "scope": str(target.payload.get("scope", "phase26")),
            "claim": "[REDACTED]",
            "provenance_refs": [target.chain_hash],
            "authority_refs": list(target.payload.get("authority_refs", [])),
            "receipt_refs": list(target.payload.get("receipt_refs", [])),
            "confidence": "verified",
            "status": "redacted_marker",
            "claim_boundary": "evidence_only",
            "redaction": {
                "redacted_entry_id": target.entry_id,
                "original_chain_hash": target.chain_hash,
                "reason_hash": content_hash({"reason": reason}),
            },
        }
        return self.append_memory_event(payload, created_at=created_at)

    def assess_fake_green(self) -> dict[str, Any]:
        for entry in self.iter_entries():
            payload = entry.to_dict()["payload"]
            if entry.schema == EXPERIENCE_ENTRY_SCHEMA and str(payload.get("result", "")).lower() == "failure":
                return {"ok": False, "reason": "failure_memory_blocks_green", "entry_id": entry.entry_id}
        return {"ok": True, "reason": "no_failure_memory"}


def evaluate_memory_driven_action(
    memory_payload: Mapping[str, Any],
    control: OperationControl | None = None,
) -> MemoryActionDecision:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=True)
    if reason:
        return MemoryActionDecision(False, reason)
    if memory_payload.get("event_type") in LIVE_ACTION_EVENTS:
        return MemoryActionDecision(False, "MEMORY_CANNOT_CREATE_LIVE_EFFECTS")
    return MemoryActionDecision(False, "MEMORY_IS_EVIDENCE_ONLY")


__all__ = [
    "ChainVerification",
    "CompactionReceipt",
    "LedgerEntry",
    "MemoryActionDecision",
    "PersistentMemoryLedger",
    "ReplayResult",
    "evaluate_memory_driven_action",
]
