"""Local durable store for operator action queue."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.operator_action_queue.errors import QueueCorruptError, SecretLeakError
from hg_runtime.operator_action_queue.schema import OperatorActionQueue

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE_ROOT = WORKSPACE / ".hg-local" / "operator_action_queue"


def default_store_paths(workspace: Path | None = None) -> tuple[Path, Path]:
    root = (workspace or WORKSPACE) / ".hg-local" / "operator_action_queue"
    return root / "operator_action_queue.json", root / "operator_action_receipts.jsonl"


def run_scoped_paths(run_dir: Path) -> tuple[Path, Path]:
    return run_dir / "operator_action_queue.json", run_dir / "operator_action_receipts.jsonl"


class OperatorQueueStore:
    """Durable local queue + append-only receipts."""

    def __init__(self, queue_path: Path, receipts_path: Path) -> None:
        self.queue_path = queue_path
        self.receipts_path = receipts_path

    @classmethod
    def default(cls, workspace: Path | None = None) -> "OperatorQueueStore":
        qp, rp = default_store_paths(workspace)
        return cls(qp, rp)

    @classmethod
    def for_run(cls, run_dir: Path) -> "OperatorQueueStore":
        qp, rp = run_scoped_paths(run_dir)
        return cls(qp, rp)

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        forbidden = scan_forbidden(payload)
        if forbidden:
            raise SecretLeakError(f"forbidden fields: {forbidden[:5]}")

    def load(self) -> OperatorActionQueue:
        if not self.queue_path.is_file():
            return OperatorActionQueue(store_root=str(self.queue_path.parent))
        try:
            data = json.loads(self.queue_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QueueCorruptError(f"corrupt queue file: {self.queue_path}") from exc
        if not isinstance(data, dict) or "items" not in data:
            raise QueueCorruptError("invalid queue schema")
        data["store_root"] = str(self.queue_path.parent)
        queue = OperatorActionQueue.from_payload(data)
        self._validate_payload(queue.to_payload())
        return queue

    def save(self, queue: OperatorActionQueue) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        payload = queue.to_payload()
        payload["store_root"] = str(self.queue_path.parent)
        self._validate_payload(payload)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        tmp = self.queue_path.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.queue_path)

    def append_receipt(self, receipt_payload: dict[str, Any]) -> str:
        self._validate_payload(receipt_payload)
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.receipts_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt_payload, sort_keys=True) + "\n")
        return str(receipt_payload.get("receipt_id", ""))

    def load_receipts(self) -> list[dict[str, Any]]:
        if not self.receipts_path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.receipts_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                raise QueueCorruptError(f"corrupt receipts: {self.receipts_path}")
        return rows


__all__ = [
    "DEFAULT_QUEUE_ROOT",
    "OperatorQueueStore",
    "default_store_paths",
    "run_scoped_paths",
]
