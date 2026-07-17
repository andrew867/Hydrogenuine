import json
import os
import shutil
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

from hg_gateway.auth import verify_api_key
from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.otel_runtime import configure_otel, shutdown_otel


class _OtlpHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.__class__.requests.append({"path": self.path, "body_len": len(body), "headers": dict(self.headers)})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):  # noqa: A003
        return


def test_otel_exports_real_otlp_http(monkeypatch):
    tmp_root = Path.cwd() / ".codex_tmp" / "testdata"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_root / f"gateway_otel_{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OtlpHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/v1/traces"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", endpoint)
    monkeypatch.setenv("HG_OTEL_SCHEDULE_DELAY_MS", "20")
    store_module._store = None
    _OtlpHandler.requests = []
    configure_otel(force=True)
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.get("/v1/system/status", headers={"X-Request-ID": "otel-test-123"})
            assert response.status_code == 200
            diag = client.get("/v1/system/diag")
            assert diag.status_code == 200
            payload = diag.json()
            assert payload["runtime"]["otel"]["enabled"] is True
            assert payload["runtime"]["otel"]["endpoint"] == endpoint
        shutdown_otel()
        deadline = time.time() + 3
        while time.time() < deadline and not _OtlpHandler.requests:
            time.sleep(0.05)
        assert _OtlpHandler.requests
        assert any(item["path"] == "/v1/traces" and item["body_len"] > 0 for item in _OtlpHandler.requests)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        shutdown_otel()
        server.shutdown()
        thread.join(timeout=2)
        shutil.rmtree(tmp_path, ignore_errors=True)

