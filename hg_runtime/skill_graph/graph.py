"""Append-only Phase 27 skill graph."""

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
from hg_runtime.skill_graph.schemas import (
    NEGATIVE_TRANSFER_SCHEMA,
    SKILL_EDGE_SCHEMA,
    SKILL_NODE_SCHEMA,
    SKILL_VERSION_SCHEMA,
    TRANSFER_CANDIDATE_SCHEMA,
    TRANSFER_EVIDENCE_SCHEMA,
    SkillGraphError,
    validate_negative_transfer,
    validate_skill_edge,
    validate_skill_node,
    validate_skill_version,
    validate_transfer_candidate,
    validate_transfer_evidence,
)

GENESIS_HASH = "sha256:phase27_genesis"


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
class SkillGraphRecord:
    record_id: str
    schema: str
    created_at: str
    payload: Mapping[str, Any]
    payload_hash: str
    previous_hash: str
    chain_hash: str

    @property
    def skill_id(self) -> str:
        return str(self.payload.get("skill_id") or self.payload.get("source_skill_id") or self.record_id)

    @property
    def skill_hash(self) -> str:
        return str(self.payload.get("skill_hash") or self.payload_hash)

    @property
    def can_authorize_tools(self) -> bool:
        return False

    @property
    def can_authorize_execution(self) -> bool:
        return False

    @property
    def can_create_live_effects(self) -> bool:
        return False

    @property
    def transfer_advisory_only(self) -> bool:
        return True

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
class SkillReplayResult:
    ok: bool
    records: int
    chain_root: str | None
    errors: list[str]


class SkillGraph:
    """Append-only advisory skill graph with deterministic replay."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._head_hash = self._load_head()

    def _load_head(self) -> str | None:
        head = None
        if self.path.exists():
            for record in self.iter_records():
                head = record.chain_hash
        return head

    def _append(self, schema: str, payload: Mapping[str, Any], *, created_at: str | None = None) -> SkillGraphRecord:
        previous = self._head_hash or GENESIS_HASH
        enriched = dict(payload)
        enriched.setdefault("record_kind", schema)
        if schema == SKILL_NODE_SCHEMA:
            seed_hash = canonical_hash(enriched)
            enriched.setdefault("skill_id", "skill-" + seed_hash.removeprefix("sha256:")[:16])
            enriched.setdefault("skill_hash", canonical_hash(enriched))
        if schema == SKILL_VERSION_SCHEMA:
            enriched.setdefault("version_hash", canonical_hash(enriched))
        payload_hash = canonical_hash(enriched)
        base = {
            "record_id": "sg-" + canonical_hash({"schema": schema, "payload_hash": payload_hash, "previous": previous}).removeprefix("sha256:")[:20],
            "schema": schema,
            "created_at": created_at or _utc_now(),
            "payload": enriched,
            "payload_hash": payload_hash,
            "previous_hash": previous,
        }
        base["chain_hash"] = _record_hash(base)
        record = SkillGraphRecord(
            record_id=base["record_id"],
            schema=schema,
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

    def iter_records(self) -> list[SkillGraphRecord]:
        if not self.path.exists():
            return []
        records: list[SkillGraphRecord] = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                data = json.loads(line)
                records.append(
                    SkillGraphRecord(
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

    def add_skill(self, payload: Mapping[str, Any], *, control: OperationControl | None = None, created_at: str | None = None) -> SkillGraphRecord:
        reason = (control or OperationControl()).refuse_reason(stop_blocks=True)
        if reason:
            raise SkillGraphError(reason)
        return self._append(SKILL_NODE_SCHEMA, validate_skill_node(payload), created_at=created_at)

    def add_edge(self, *, source_id: str, target_id: str, edge_type: str, evidence_refs: list[str], receipt_refs: list[str]) -> SkillGraphRecord:
        return self._append(
            SKILL_EDGE_SCHEMA,
            validate_skill_edge(
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "edge_type": edge_type,
                    "evidence_refs": evidence_refs,
                    "receipt_refs": receipt_refs,
                }
            ),
        )

    def add_skill_version(self, skill_id: str, *, parent_refs: list[str], change_summary: str) -> SkillGraphRecord:
        return self._append(
            SKILL_VERSION_SCHEMA,
            validate_skill_version(
                {
                    "skill_id": skill_id,
                    "parent_refs": parent_refs,
                    "change_summary": change_summary,
                    "evidence_refs": parent_refs,
                    "receipt_refs": ["receipt:phase27:skill_version"],
                }
            ),
        )

    def add_transfer_candidate(self, payload: Mapping[str, Any], *, control: OperationControl | None = None, created_at: str | None = None) -> SkillGraphRecord:
        reason = (control or OperationControl()).refuse_reason(stop_blocks=True)
        if reason:
            raise SkillGraphError(reason)
        return self._append(TRANSFER_CANDIDATE_SCHEMA, validate_transfer_candidate(payload), created_at=created_at)

    def record_transfer_evidence(self, skill_id: str, *, result: str, evidence_refs: list[str], receipt_refs: list[str]) -> SkillGraphRecord:
        return self._append(
            TRANSFER_EVIDENCE_SCHEMA,
            validate_transfer_evidence(
                {
                    "skill_id": skill_id,
                    "result": result,
                    "evidence_refs": evidence_refs,
                    "receipt_refs": receipt_refs,
                    "claim_boundary": "advisory_only",
                }
            ),
        )

    def record_negative_transfer(self, payload: Mapping[str, Any]) -> SkillGraphRecord:
        return self._append(NEGATIVE_TRANSFER_SCHEMA, validate_negative_transfer(payload))

    def replay(self, *, control: OperationControl | None = None) -> SkillReplayResult:
        reason = (control or OperationControl()).refuse_reason()
        if reason:
            raise SkillGraphError(reason)
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
        return SkillReplayResult(ok=not errors, records=count, chain_root=head, errors=errors)

    def query(
        self,
        *,
        skill_id: str | None = None,
        domain: str | None = None,
        evidence_ref: str | None = None,
        provenance_ref: str | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for record in self.iter_records():
            payload = record.to_dict()["payload"]
            if skill_id and payload.get("skill_id") != skill_id:
                continue
            if domain and payload.get("domain") != domain and payload.get("source_domain") != domain and payload.get("target_domain") != domain:
                continue
            if evidence_ref and evidence_ref not in payload.get("evidence_refs", []):
                continue
            if provenance_ref and provenance_ref not in payload.get("provenance_refs", []):
                continue
            results.append({"record_id": record.record_id, "skill_id": payload.get("skill_id"), "schema": record.schema, **payload})
        return results


__all__ = ["GENESIS_HASH", "SkillGraph", "SkillGraphRecord", "SkillReplayResult"]
