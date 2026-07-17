"""Watchtower sidecar lifecycle — explicit autostart, local-only, lifecycle receipts."""

from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.openvino_watchtower.runtime_config import LIFECYCLE_DIR, load_runtime_config, validate_host

_sidecar_lock = threading.Lock()
_sidecar_thread: threading.Thread | None = None
_sidecar_server: Any = None
_sidecar_started = False


@dataclass
class LifecycleResult:
    ok: bool
    verdict: str
    message: str
    receipt_path: str | None = None
    reused: bool = False
    authority_created: bool = False
    permission_granted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "verdict": self.verdict,
            "message": self.message,
            "receipt_path": self.receipt_path,
            "reused": self.reused,
            "authority_created": False,
            "permission_granted": False,
        }


def _write_receipt(kind: str, payload: dict[str, Any]) -> Path:
    LIFECYCLE_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = LIFECYCLE_DIR / f"{kind}_{ts}.json"
    body = {"kind": kind, "ts": ts, **payload, "authority_created": False, "permission_granted": False}
    path.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def start_sidecar(*, force: bool = False) -> LifecycleResult:
    global _sidecar_thread, _sidecar_server, _sidecar_started
    cfg = load_runtime_config()
    ok_host, host_err = validate_host(cfg.host)
    if not ok_host:
        receipt = _write_receipt("autostart_denied", {"reason": host_err, "host": cfg.host})
        return LifecycleResult(False, "RED_EXTERNAL_BIND", host_err or "external bind denied", str(receipt))

    with _sidecar_lock:
        if _sidecar_started or _port_open(cfg.host, cfg.port):
            receipt = _write_receipt("autostart_reused", {"host": cfg.host, "port": cfg.port})
            return LifecycleResult(True, "GREEN_OPENVINO_WATCHTOWER_SIDECAR_REUSED", "existing sidecar reused", str(receipt), reused=True)

        try:
            from hg_runtime.openvino_watchtower.server import OpenVINOWatchtowerServer

            server = OpenVINOWatchtowerServer(host=cfg.host, port=cfg.port, enable_metrics=cfg.prometheus_enabled)
            server.start(background=True)
            _sidecar_server = server
            _sidecar_started = True
            receipt = _write_receipt("autostart_started", {"host": cfg.host, "port": cfg.port})
            return LifecycleResult(True, "GREEN_OPENVINO_WATCHTOWER_SIDECAR_STARTED", "sidecar started", str(receipt))
        except Exception as exc:
            receipt = _write_receipt("autostart_failed", {"error": str(exc), "strict_start": cfg.strict_start})
            verdict = "RED_AUTOSTART_FAILED" if cfg.strict_start else "YELLOW_OPENVINO_WATCHTOWER_AUTOSTART_DEGRADED"
            return LifecycleResult(not cfg.strict_start, verdict, str(exc), str(receipt))


def stop_sidecar() -> LifecycleResult:
    global _sidecar_thread, _sidecar_server, _sidecar_started
    with _sidecar_lock:
        if _sidecar_server is not None:
            try:
                _sidecar_server.stop()
            except Exception:
                pass
        _sidecar_server = None
        _sidecar_thread = None
        _sidecar_started = False
        receipt = _write_receipt("autostart_stopped", {})
        return LifecycleResult(True, "GREEN_OPENVINO_WATCHTOWER_SIDECAR_STOPPED", "sidecar stopped", str(receipt))


def maybe_autostart_watchtower() -> LifecycleResult | None:
    cfg = load_runtime_config()
    if not cfg.enabled or not cfg.autostart:
        return None
    return start_sidecar()


__all__ = ["LifecycleResult", "maybe_autostart_watchtower", "start_sidecar", "stop_sidecar"]
