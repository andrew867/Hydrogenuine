"""Local-only HTTP server for watchtower status, events, SSE stream, and metrics."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector, get_collector
from hg_runtime.openvino_watchtower.events import add_listener, default_port, read_recent_events, remove_listener
from hg_runtime.openvino_watchtower.prometheus_exporter import render_prometheus_metrics
from hg_runtime.openvino_watchtower.redaction import redact_payload
from hg_runtime.openvino_watchtower.replay import WatchtowerReplay
from hg_runtime.openvino_watchtower.schema import TelemetryRedactionPolicy
from hg_runtime.openvino_watchtower.session import list_sessions

WORKSPACE = Path(__file__).resolve().parents[2]


class _SSEBroadcaster:
    def __init__(self) -> None:
        self._clients: list[Any] = []
        self._lock = threading.Lock()

    def subscribe(self, wfile) -> None:
        with self._lock:
            self._clients.append(wfile)

    def unsubscribe(self, wfile) -> None:
        with self._lock:
            if wfile in self._clients:
                self._clients.remove(wfile)

    def publish(self, payload: dict[str, Any]) -> None:
        line = f"data: {json.dumps(payload, sort_keys=True)}\n\n".encode("utf-8")
        dead: list[Any] = []
        with self._lock:
            clients = list(self._clients)
        for wfile in clients:
            try:
                wfile.write(line)
                wfile.flush()
            except Exception:
                dead.append(wfile)
        for wfile in dead:
            self.unsubscribe(wfile)


class OpenVINOWatchtowerServer:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int | None = None,
        collector: OpenVINOWatchtowerCollector | None = None,
        enable_metrics: bool = True,
    ) -> None:
        self.host = host
        self.port = port or default_port()
        self.collector = collector or get_collector()
        self.enable_metrics = enable_metrics
        self._broadcaster = _SSEBroadcaster()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._listener = self._on_event

    def _on_event(self, event: dict[str, Any]) -> None:
        redacted, _ = redact_payload(event, policy=TelemetryRedactionPolicy())
        self._broadcaster.publish(redacted)
        self.collector.ingest_event(event)

    def start(self, *, background: bool = True) -> None:
        add_listener(self._listener)
        self.collector.start()
        handler = self._make_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        if background:
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        else:
            self._httpd.serve_forever()

    def stop(self) -> None:
        remove_listener(self._listener)
        self.collector.stop()
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None

    def _make_handler(self):
        collector = self.collector
        broadcaster = self._broadcaster
        enable_metrics = self.enable_metrics
        host = self.host

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

            def _send_json(self, code: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_text(self, code: int, body: str, content_type: str) -> None:
                raw = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                if self.server.server_address[0] != host and host != "127.0.0.1":
                    self._send_json(403, {"error": "bind mismatch"})
                    return
                path = urlparse(self.path).path
                if path == "/status":
                    snap = collector.snapshot()
                    self._send_json(200, snap)
                    return
                if path == "/events":
                    events = read_recent_events(200)
                    redacted = [redact_payload(e)[0] for e in events]
                    self._send_json(200, {"events": redacted, "count": len(redacted)})
                    return
                if path == "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    broadcaster.subscribe(self.wfile)
                    try:
                        snap = collector.snapshot()
                        self.wfile.write(f"data: {json.dumps(snap, sort_keys=True)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        while True:
                            time.sleep(15)
                            snap = collector.snapshot()
                            self.wfile.write(f"data: {json.dumps(snap, sort_keys=True)}\n\n".encode("utf-8"))
                            self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    finally:
                        broadcaster.unsubscribe(self.wfile)
                    return
                if path == "/sessions":
                    self._send_json(200, {"sessions": list_sessions(), "authority_created": False})
                    return
                if path.startswith("/replay/"):
                    sid = path.split("/replay/", 1)[1].strip("/")
                    replay = WatchtowerReplay.open(sid)
                    replay.assert_read_only()
                    self._send_json(
                        200,
                        {
                            "session_id": sid,
                            "snapshot": replay.snapshot(),
                            "events": replay.events(),
                            "timeline": replay.timeline(),
                            "replay_mode": "read_only",
                            "authority_created": False,
                        },
                    )
                    return
                if path == "/metrics" and enable_metrics:
                    snap = collector.snapshot(persist=False)
                    self._send_text(200, render_prometheus_metrics(snap), "text/plain; version=0.0.4")
                    return
                self._send_json(
                    404,
                    {
                        "error": "not_found",
                        "paths": ["/status", "/events", "/stream", "/sessions", "/replay/<id>", "/metrics", "POST /incident/export"],
                    },
                )

            def do_POST(self) -> None:  # noqa: N802
                if self.server.server_address[0] != host and host != "127.0.0.1":
                    self._send_json(403, {"error": "bind mismatch"})
                    return
                path = urlparse(self.path).path
                if path != "/incident/export":
                    self._send_json(404, {"error": "not_found"})
                    return
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    self._send_json(400, {"ok": False, "error": "invalid_json"})
                    return
                session_id = str(body.get("session_id") or "").strip()
                incident_id = str(body.get("incident_id") or "").strip()
                reason = str(body.get("reason") or "operator_export").strip()
                if not session_id or not incident_id:
                    self._send_json(400, {"ok": False, "error": "session_id and incident_id required"})
                    return
                from hg_runtime.openvino_watchtower.incident_export import export_incident

                try:
                    out = export_incident(session_id=session_id, incident_id=incident_id, reason=reason)
                    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
                    privacy_path = out / "privacy_report.json"
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "export_path": str(out),
                            "manifest_hash": manifest.get("snapshot_hash"),
                            "privacy_report_path": str(privacy_path),
                            "redaction_applied": True,
                            "authority_created": False,
                            "permission_granted": False,
                        },
                    )
                except Exception as exc:
                    self._send_json(500, {"ok": False, "error": str(exc), "authority_created": False})

        return Handler


__all__ = ["OpenVINOWatchtowerServer"]
