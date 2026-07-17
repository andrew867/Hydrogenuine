"""Broker audit log — append-only JSONL with hash chain."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.capability_broker.errors import BrokerAuditError
from hg_runtime.capability_broker.redaction import has_forbidden_audit_field
from hg_runtime.capability_broker.schema import BrokerAuditRecord, BrokerDecision


@dataclass
class BrokerAuditLog:
    path: Path

    def ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: BrokerAuditRecord) -> None:
        payload = record.to_payload()
        if has_forbidden_audit_field(payload):
            raise BrokerAuditError("audit record contains secret or hidden cot")
        self.ensure_parent()
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        entries: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
        return entries

    def verify_chain(self) -> None:
        entries = self.read_all()
        prev_hash: str | None = None
        for i, entry in enumerate(entries):
            if i > 0 and entry.get("previous_record_hash") != prev_hash:
                raise BrokerAuditError(
                    f"audit hash chain break: expected {prev_hash}, got {entry.get('previous_record_hash')}"
                )
            prev_hash = entry.get("hash")


def audit_path_for_run(run_id: str, *, base: Path | None = None) -> Path:
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "broker"
    return root / run_id / "broker_audit.jsonl"


def record_from_decision(
    decision: BrokerDecision,
    *,
    request_id: str,
    previous_record_hash: str | None = None,
) -> BrokerAuditRecord:
    record = BrokerAuditRecord(
        record_id=f"audit-{uuid.uuid4().hex[:12]}",
        decision_id=decision.decision_id,
        request_id=request_id,
        agent_id=decision.agent_id,
        turn_index=decision.turn_index,
        chosen_action=decision.chosen_action,
        verdict=decision.verdict.value,
        status=decision.status.value,
        admitted=decision.admitted,
        refused=decision.refused,
        refusal_reasons=list(decision.refusal_reasons),
        created_at=decision.created_at,
        previous_record_hash=previous_record_hash,
    ).with_hash()
    return record


def append_decision_to_audit(
    log: BrokerAuditLog,
    decision: BrokerDecision,
    *,
    request_id: str,
) -> BrokerAuditRecord:
    entries = log.read_all()
    prev = entries[-1]["hash"] if entries else None
    record = record_from_decision(decision, request_id=request_id, previous_record_hash=prev)
    log.append(record)
    log.verify_chain()
    return record


__all__ = [
    "BrokerAuditLog",
    "append_decision_to_audit",
    "audit_path_for_run",
    "record_from_decision",
]
