"""Local HTTP server for the operator review UI.

Serves the operator console HTML and handles decision API calls.
Playwright opens this server, clicks approve/deny, and the server
writes signed receipts to the proof bundle directory.
"""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner


class _Handler(BaseHTTPRequestHandler):
    signer: OperatorSigner
    bundle_dir: Path
    ui_html: str
    review_data: dict
    decisions_made: list

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self._respond(200, "text/html", self.ui_html.encode("utf-8"))
        elif self.path == "/api/review-data":
            self._respond(200, "application/json", json.dumps(self.review_data).encode("utf-8"))
        elif self.path == "/api/decisions":
            self._respond(200, "application/json", json.dumps(self.decisions_made).encode("utf-8"))
        else:
            self._respond(404, "text/plain", b"not found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/decide":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            action = body.get("action", "")
            candidate_id = body.get("candidate_id", "")
            reason = body.get("reason", "")
            receipt_ids = body.get("receipt_ids_reviewed", [])

            if action not in ("approve", "deny", "hold"):
                self._respond(400, "application/json", json.dumps({"error": "invalid action"}).encode())
                return

            decision = self.signer.sign_decision(
                action=action,
                target_candidate_id=candidate_id,
                reason=reason,
                receipt_ids_reviewed=receipt_ids,
            )

            filename = f"operator_decision_{action}_{candidate_id}.json"
            filepath = self.bundle_dir / filename
            filepath.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            self.decisions_made.append(decision)

            self._respond(200, "application/json", json.dumps(decision).encode("utf-8"))
        else:
            self._respond(404, "text/plain", b"not found")

    def _respond(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_operator_server(
    *,
    signer: OperatorSigner,
    bundle_dir: Path,
    ui_html: str,
    review_data: dict,
    port: int = 0,
) -> tuple[HTTPServer, int, list]:
    """Start operator review server. Returns (server, port, decisions_list)."""
    decisions_made: list = []

    class Handler(_Handler):
        pass

    Handler.signer = signer
    Handler.bundle_dir = bundle_dir
    Handler.ui_html = ui_html
    Handler.review_data = review_data
    Handler.decisions_made = decisions_made

    server = HTTPServer(("127.0.0.1", port), Handler)
    actual_port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server, actual_port, decisions_made
