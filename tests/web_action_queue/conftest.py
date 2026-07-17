"""Web action queue test fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_action_queue.queue import OperatorQueueRuntime
from hg_runtime.operator_action_queue.store import OperatorQueueStore
from hg_runtime.web_action_queue.queue import WebActionQueueRuntime, WebActionQueueStore


def make_runtime(tmp_path: Path, *, live_browser: bool = False) -> WebActionQueueRuntime:
    wroot = tmp_path / "web"
    oroot = tmp_path / "operator"
    wstore = WebActionQueueStore(
        wroot / "web_action_queue.json",
        wroot / "web_action_receipts.jsonl",
    )
    ostore = OperatorQueueStore(
        oroot / "operator_action_queue.json",
        oroot / "operator_action_receipts.jsonl",
    )
    oq = OperatorQueueRuntime(ostore)
    return WebActionQueueRuntime(
        wstore,
        operator_queue=oq,
        live_browser_enabled=live_browser,
        workspace=tmp_path,
    )
