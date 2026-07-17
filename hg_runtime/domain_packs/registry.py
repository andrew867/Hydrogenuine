"""Append-only Phase 28 domain pack registry."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.domain_packs.activation import activate_domain_pack
from hg_runtime.domain_packs.loader import load_domain_pack
from hg_runtime.domain_packs.schemas import DOMAIN_PACK_ACTIVATION_RECEIPT_SCHEMA, DOMAIN_PACK_SCHEMA, DomainPackError

GENESIS_HASH = "sha256:phase28_genesis"


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


def _record_hash(record: Mapping[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "chain_hash"}
    return canonical_hash(body)


@dataclass(frozen=True)
class DomainPackRecord:
    record_id: str
    schema: str
    created_at: str
    payload: Mapping[str, Any]
    payload_hash: str
    previous_hash: str
    chain_hash: str

    @property
    def can_authorize_tools(self) -> bool:
        return False

    @property
    def can_create_live_effects(self) -> bool:
        return False

    @property
    def can_expand_authority(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "schema": self.schema,
            "created_at": self.created_at,
            "payload": _plain(self.payload),
            "payload_hash": self.payload_hash,
            "previous_hash": self.previous_hash,
            "chain_hash": self.chain_hash,
        }


@dataclass(frozen=True)
class DomainPackReplayResult:
    ok: bool
    records: int
    chain_root: str | None
    errors: list[str]


class DomainPackRegistry:
    """Append-only registry for declarative domain packs and activation receipts."""

    def __init__(
        self,
        path: Path,
        *,
        known_tool_refs: set[str] | None = None,
        known_skill_refs: set[str] | None = None,
        known_memory_refs: set[str] | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.known_tool_refs = known_tool_refs or set()
        self.known_skill_refs = known_skill_refs or set()
        self.known_memory_refs = known_memory_refs or set()
        self._head_hash = self._load_head()

    def _load_head(self) -> str | None:
        head = None
        if self.path.exists():
            for record in self.iter_records():
                head = record.chain_hash
        return head

    def _append(self, schema: str, payload: Mapping[str, Any], *, created_at: str | None = None) -> DomainPackRecord:
        previous = self._head_hash or GENESIS_HASH
        enriched = dict(payload)
        enriched.setdefault("record_kind", schema)
        payload_hash = canonical_hash(enriched)
        base = {
            "record_id": "dp-" + canonical_hash({"schema": schema, "payload_hash": payload_hash, "previous": previous}).removeprefix("sha256:")[:20],
            "schema": schema,
            "created_at": created_at or _utc_now(),
            "payload": enriched,
            "payload_hash": payload_hash,
            "previous_hash": previous,
        }
        base["chain_hash"] = _record_hash(base)
        record = DomainPackRecord(
            record_id=base["record_id"],
            schema=base["schema"],
            created_at=base["created_at"],
            payload=_immutable(base["payload"]),
            payload_hash=base["payload_hash"],
            previous_hash=base["previous_hash"],
            chain_hash=base["chain_hash"],
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._head_hash = record.chain_hash
        return record

    def iter_records(self) -> list[DomainPackRecord]:
        if not self.path.exists():
            return []
        records: list[DomainPackRecord] = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                data = json.loads(line)
                records.append(
                    DomainPackRecord(
                        record_id=data["record_id"],
                        schema=data["schema"],
                        created_at=data["created_at"],
                        payload=_immutable(data["payload"]),
                        payload_hash=data["payload_hash"],
                        previous_hash=data["previous_hash"],
                        chain_hash=data["chain_hash"],
                    )
                )
        return records

    def load_pack(self, payload: Mapping[str, Any], *, control: OperationControl | None = None, created_at: str | None = None) -> DomainPackRecord:
        pack = load_domain_pack(
            payload,
            known_tool_refs=self.known_tool_refs,
            known_skill_refs=self.known_skill_refs,
            known_memory_refs=self.known_memory_refs,
            control=control,
        )
        return self._append(DOMAIN_PACK_SCHEMA, pack, created_at=created_at)

    def activate_pack(
        self,
        pack: Mapping[str, Any],
        *,
        phase26_verdict: str,
        phase27_verdict: str,
        receipt_refs: list[str],
        control: OperationControl | None = None,
        created_at: str | None = None,
    ) -> DomainPackRecord:
        receipt = activate_domain_pack(
            pack,
            phase26_verdict=phase26_verdict,
            phase27_verdict=phase27_verdict,
            receipt_refs=receipt_refs,
            control=control,
            activated_at=created_at,
        )
        return self._append(DOMAIN_PACK_ACTIVATION_RECEIPT_SCHEMA, receipt, created_at=created_at)

    def record_version_change(self, pack: Mapping[str, Any], *, parent_pack_hash: str, change_summary: str) -> DomainPackRecord:
        if not parent_pack_hash:
            raise DomainPackError("provenance_required:pack_version_change_requires_parent_hash")
        payload = {
            "domain_id": pack["domain_id"],
            "version": pack["version"],
            "pack_hash": pack["pack_hash"],
            "parent_pack_hash": parent_pack_hash,
            "change_summary": change_summary,
            "authority_created": False,
            "permission_granted": False,
        }
        return self._append("domain_pack_version_record_v1", payload)

    def replay(self, *, control: OperationControl | None = None) -> DomainPackReplayResult:
        reason = (control or OperationControl()).refuse_reason()
        if reason:
            raise DomainPackError(reason)
        errors: list[str] = []
        previous = GENESIS_HASH
        head: str | None = None
        count = 0
        for record in self.iter_records():
            data = record.to_dict()
            if data["previous_hash"] != previous:
                errors.append(f"chain_break:{record.record_id}")
            if canonical_hash(data["payload"]) != data["payload_hash"]:
                errors.append(f"payload_hash_mismatch:{record.record_id}")
            if _record_hash(data) != data["chain_hash"]:
                errors.append(f"chain_hash_mismatch:{record.record_id}")
            previous = data["chain_hash"]
            head = previous
            count += 1
        return DomainPackReplayResult(ok=not errors, records=count, chain_root=head, errors=errors)

    def query(self, *, domain_id: str | None = None, pack_hash: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for record in self.iter_records():
            payload = record.to_dict()["payload"]
            if domain_id and payload.get("domain_id") != domain_id:
                continue
            if pack_hash and payload.get("pack_hash") != pack_hash:
                continue
            results.append({"record_id": record.record_id, "schema": record.schema, **payload})
        return results


__all__ = ["GENESIS_HASH", "DomainPackRecord", "DomainPackRegistry", "DomainPackReplayResult"]
