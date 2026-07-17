"""Web action queue runtime — no execution."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.operator_action_queue.queue import OperatorQueueRuntime
from hg_runtime.operator_action_queue.store import OperatorQueueStore
from hg_runtime.operator_action_queue.stop_panic_policy import load_stop_panic_state
from hg_runtime.web_action_queue.adapters import web_action_to_operator_queue_item
from hg_runtime.web_action_queue.errors import WebQueueCorruptError, WebSecretExposureError
from hg_runtime.web_action_queue.policy import classify_web_policy, is_denied, requires_operator_queue
from hg_runtime.web_action_queue.quarantine import create_quarantine_metadata
from hg_runtime.web_action_queue.receipts import receipt_for_policy
from hg_runtime.web_action_queue.schema import (
    WebActionDecisionKind,
    WebActionQueue,
    WebActionRequest,
    WebActionStatus,
)

WORKSPACE = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebActionQueueStore:
    def __init__(self, queue_path: Path, receipts_path: Path) -> None:
        self.queue_path = queue_path
        self.receipts_path = receipts_path

    @classmethod
    def default(cls, workspace: Path | None = None) -> "WebActionQueueStore":
        root = (workspace or WORKSPACE) / ".hg-local" / "web_action_queue"
        return cls(root / "web_action_queue.json", root / "web_action_receipts.jsonl")

    def load(self) -> WebActionQueue:
        if not self.queue_path.is_file():
            return WebActionQueue(store_root=str(self.queue_path.parent))
        try:
            data = json.loads(self.queue_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WebQueueCorruptError(str(exc)) from exc
        return WebActionQueue.from_payload(data)

    def save(self, queue: WebActionQueue) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        payload = queue.to_payload()
        forbidden = scan_forbidden(payload)
        if forbidden:
            raise WebSecretExposureError(str(forbidden[:5]))
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        tmp = self.queue_path.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.queue_path)

    def append_receipt(self, payload: dict[str, Any]) -> None:
        forbidden = scan_forbidden(payload)
        if forbidden:
            raise WebSecretExposureError(str(forbidden[:5]))
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.receipts_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")


class WebActionQueueRuntime:
    """Web action queue — classifies, queues, never executes."""

    def __init__(
        self,
        store: WebActionQueueStore,
        *,
        operator_queue: OperatorQueueRuntime | None = None,
        live_browser_enabled: bool = False,
        workspace: Path | None = None,
    ) -> None:
        self.store = store
        self.workspace = workspace or WORKSPACE
        self.live_browser_enabled = live_browser_enabled
        self._queue = self.store.load()
        if operator_queue is None:
            ostore = OperatorQueueStore.default(self.workspace)
            self._operator_queue = OperatorQueueRuntime(ostore)
        else:
            self._operator_queue = operator_queue

    def _stop_panic(self):
        return load_stop_panic_state(self.workspace)

    def enqueue(self, request: WebActionRequest) -> WebActionRequest:
        sp = self._stop_panic()
        policy = classify_web_policy(
            request.action_type,
            trust_boundary_verdict=request.trust_boundary_verdict,
            live_browser_enabled=self.live_browser_enabled,
            cargo_text=request.cargo_summary.excerpt,
            stop_active=sp.stop_active,
            panic_active=sp.panic_active,
        )

        if is_denied(policy):
            request.status = WebActionStatus.DENIED
        elif policy.decision == WebActionDecisionKind.ALLOW_READ_ONLY:
            request.status = WebActionStatus.EXECUTED_READ_ONLY
        elif policy.decision == WebActionDecisionKind.DRY_RUN_ONLY:
            request.status = WebActionStatus.DRY_RUN_ONLY
        elif policy.decision == WebActionDecisionKind.QUARANTINE_DOWNLOAD:
            request.status = WebActionStatus.QUARANTINED
            qref = create_quarantine_metadata(
                original_url=request.target_url or "",
                filename=request.download_filename or "download.bin",
                source_action_ref=request.web_action_id,
                workspace=self.workspace,
            )
            request.quarantine_ref = qref.quarantine_id
        else:
            request.status = WebActionStatus.QUEUED

        receipt = receipt_for_policy(request, policy.decision, policy.reason)
        request.receipt_ref = receipt.receipt_id
        self.store.append_receipt(receipt.to_payload())

        if requires_operator_queue(policy) and request.status == WebActionStatus.QUEUED:
            oitem = web_action_to_operator_queue_item(request)
            enqueued = self._operator_queue.enqueue(oitem.action_request)
            request.operator_queue_item_ref = enqueued.queue_item_id

        self._queue.items.append(request)
        self.store.save(self._queue)
        return request

    def list_items(self) -> list[WebActionRequest]:
        return list(self._queue.items)

    def get_item(self, web_action_id: str) -> WebActionRequest | None:
        for item in self._queue.items:
            if item.web_action_id == web_action_id:
                return item
        return None

    def summarize(self) -> dict[str, Any]:
        sp = self._stop_panic()
        counts: dict[str, int] = {}
        for item in self._queue.items:
            counts[item.status.value] = counts.get(item.status.value, 0) + 1
        return {
            "total": len(self._queue.items),
            "counts": counts,
            "live_browser_enabled": self.live_browser_enabled,
            "stop_active": sp.stop_active,
            "panic_active": sp.panic_active,
            "queue_path": str(self.store.queue_path),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def open_web_queue(
    workspace: Path | None = None,
    *,
    live_browser_enabled: bool = False,
    operator_queue: OperatorQueueRuntime | None = None,
) -> WebActionQueueRuntime:
    store = WebActionQueueStore.default(workspace)
    return WebActionQueueRuntime(
        store,
        operator_queue=operator_queue,
        live_browser_enabled=live_browser_enabled,
        workspace=workspace,
    )


__all__ = [
    "WebActionQueueRuntime",
    "WebActionQueueStore",
    "open_web_queue",
]
