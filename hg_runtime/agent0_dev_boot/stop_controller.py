"""Runtime stop, panic, and cleanup discipline."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from hg_runtime.agent0_dev_boot.types import FIXTURE_CLOCK, advisory_payload

DEFAULT_PANIC_FILE = Path(".hg-local/runtime/agent0_dev_boot.panic")
DEFAULT_RUN_ROOT = Path(".hg-local/runtime/runs")


@dataclass
class RuntimeStopController:
    run_id: str
    panic_file: Path = DEFAULT_PANIC_FILE
    max_duration_seconds: int = 600
    panic_after_seconds: int | None = None
    stopped: bool = False
    stop_reason: str = ""
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def panic_requested(self) -> bool:
        return self.panic_file.is_file()

    def budget_exceeded(self, started: float, clock: Callable[[], float] | None = None) -> bool:
        clock = clock or time.monotonic
        elapsed = clock() - started
        if elapsed >= self.max_duration_seconds:
            return True
        if self.panic_after_seconds is not None and elapsed >= self.panic_after_seconds:
            return True
        return False

    def request_stop(self, reason: str) -> None:
        self.stopped = True
        self.stop_reason = reason
        self.receipts.append(
            advisory_payload(schema="runtime-stop-receipt", run_id=self.run_id, reason=reason, observed_at=FIXTURE_CLOCK)
        )

    def panic_stop(self) -> None:
        self.request_stop("panic_stop")

    def cleanup_receipt(self) -> dict[str, Any]:
        receipt = advisory_payload(
            schema="cleanup-receipt",
            run_id=self.run_id,
            panic_file=str(self.panic_file),
            stopped=self.stopped,
            stop_reason=self.stop_reason,
            observed_at=FIXTURE_CLOCK,
        )
        self.receipts.append(receipt)
        return receipt

    def orphan_container_check(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            ok = result.returncode == 0
            detail = result.stdout[:2000] if ok else result.stderr[:500]
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok = False
            detail = str(exc)
        return advisory_payload(schema="orphan-container-check", run_id=self.run_id, ok=ok, detail=detail)

    def provider_pid_check(self, pid_file: Path | None = None) -> dict[str, Any]:
        pid_path = pid_file or Path(".hg-local/openvino-provider/provider.pid")
        stale = False
        if pid_path.is_file():
            stale = True
        return advisory_payload(schema="provider-pid-check", run_id=self.run_id, pid_file=str(pid_path), stale_pid_file=stale)


def new_run_dir(run_id: str | None = None) -> Path:
    rid = run_id or f"agent0-{uuid.uuid4().hex[:12]}"
    path = DEFAULT_RUN_ROOT / rid
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_final_digest(run_dir: Path, events: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> dict[str, Any]:
    digest = advisory_payload(
        schema="runtime-final-digest",
        run_id=run_dir.name,
        event_count=len(events),
        receipt_count=len(receipts),
        observed_at=FIXTURE_CLOCK,
    )
    (run_dir / "final_digest.json").write_text(json.dumps(digest, indent=2), encoding="utf-8")
    return digest


__all__ = [
    "DEFAULT_PANIC_FILE",
    "DEFAULT_RUN_ROOT",
    "RuntimeStopController",
    "new_run_dir",
    "write_final_digest",
]
