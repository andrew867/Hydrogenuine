"""Field run receipts — start, checkpoint, stop."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.schema import field_run_dir, new_id, now_iso


@dataclass
class FieldRunStartReceipt:
    start_receipt_id: str
    field_run_id: str
    config_hash: str
    mode: str
    pid: int
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "start_receipt_id": self.start_receipt_id,
            "field_run_id": self.field_run_id,
            "config_hash": self.config_hash,
            "mode": self.mode,
            "pid": self.pid,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> FieldRunStartReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return FieldRunStartReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class FieldRunCheckpointReceipt:
    checkpoint_receipt_id: str
    field_run_id: str
    turn_count: int
    task_selection_count: int
    governed_work_count: int
    heartbeat_ref: str
    external_side_effect_count: int
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "checkpoint_receipt_id": self.checkpoint_receipt_id,
            "field_run_id": self.field_run_id,
            "turn_count": self.turn_count,
            "task_selection_count": self.task_selection_count,
            "governed_work_count": self.governed_work_count,
            "heartbeat_ref": self.heartbeat_ref,
            "external_side_effect_count": self.external_side_effect_count,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> FieldRunCheckpointReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return FieldRunCheckpointReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class FieldRunStopReceipt:
    stop_receipt_id: str
    field_run_id: str
    stop_reason: str
    turn_count: int
    panic_requested: bool
    stop_requested: bool
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "stop_receipt_id": self.stop_receipt_id,
            "field_run_id": self.field_run_id,
            "stop_reason": self.stop_reason,
            "turn_count": self.turn_count,
            "panic_requested": self.panic_requested,
            "stop_requested": self.stop_requested,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> FieldRunStopReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return FieldRunStopReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


def _receipts_dir(field_run_id: str, *, base: Path | None = None) -> Path:
    d = field_run_dir(field_run_id, base=base) / "receipts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def persist_start_receipt(receipt: FieldRunStartReceipt, *, base: Path | None = None) -> Path:
    path = _receipts_dir(receipt.field_run_id, base=base) / f"{receipt.start_receipt_id}.json"
    path.write_text(json.dumps(receipt.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def persist_checkpoint_receipt(receipt: FieldRunCheckpointReceipt, *, base: Path | None = None) -> Path:
    path = _receipts_dir(receipt.field_run_id, base=base) / f"{receipt.checkpoint_receipt_id}.json"
    path.write_text(json.dumps(receipt.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def persist_stop_receipt(receipt: FieldRunStopReceipt, *, base: Path | None = None) -> Path:
    path = _receipts_dir(receipt.field_run_id, base=base) / f"{receipt.stop_receipt_id}.json"
    path.write_text(json.dumps(receipt.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def list_checkpoint_receipts(field_run_id: str, *, base: Path | None = None) -> list[FieldRunCheckpointReceipt]:
    d = _receipts_dir(field_run_id, base=base)
    out: list[FieldRunCheckpointReceipt] = []
    for p in sorted(d.glob("checkpoint-*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append(FieldRunCheckpointReceipt(**data))
    return out


def make_start_receipt(field_run_id: str, config_hash: str, mode: str, pid: int) -> FieldRunStartReceipt:
    return FieldRunStartReceipt(
        start_receipt_id=new_id("start"),
        field_run_id=field_run_id,
        config_hash=config_hash,
        mode=mode,
        pid=pid,
        created_at=now_iso(),
    ).with_hash()


def make_checkpoint_receipt(
    field_run_id: str,
    *,
    turn_count: int,
    task_selection_count: int,
    governed_work_count: int,
    heartbeat_ref: str,
    external_side_effect_count: int,
) -> FieldRunCheckpointReceipt:
    return FieldRunCheckpointReceipt(
        checkpoint_receipt_id=new_id("checkpoint"),
        field_run_id=field_run_id,
        turn_count=turn_count,
        task_selection_count=task_selection_count,
        governed_work_count=governed_work_count,
        heartbeat_ref=heartbeat_ref,
        external_side_effect_count=external_side_effect_count,
        created_at=now_iso(),
    ).with_hash()


def make_stop_receipt(
    field_run_id: str,
    *,
    stop_reason: str,
    turn_count: int,
    panic_requested: bool,
    stop_requested: bool,
) -> FieldRunStopReceipt:
    return FieldRunStopReceipt(
        stop_receipt_id=new_id("stop"),
        field_run_id=field_run_id,
        stop_reason=stop_reason,
        turn_count=turn_count,
        panic_requested=panic_requested,
        stop_requested=stop_requested,
        created_at=now_iso(),
    ).with_hash()
