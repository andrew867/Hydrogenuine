"""Small standard-library client for the local Community gateway."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class GatewayError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class GatewayClient:
    def __init__(self, api_base: str, *, auth_mode: str = "local-no-key", timeout: float = 10.0) -> None:
        self.api_base = api_base.rstrip("/")
        self.auth_mode = auth_mode
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json", "content-type": "application/json"}
        if self.auth_mode == "api-key":
            key = os.environ.get("HG_GATEWAY_API_KEY", "").strip()
            if key:
                headers["x-api-key"] = key
        return headers

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            self.api_base + path,
            data=payload,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
                detail = data.get("detail") or data.get("reason") or raw
            except json.JSONDecodeError:
                detail = raw or exc.reason
            if exc.code == 401:
                if self.auth_mode == "local-no-key":
                    detail = "The local gateway is not in no-key mode. Run 'hg doctor' and restart it with the Community start script."
                else:
                    detail = "The gateway rejected HG_GATEWAY_API_KEY. This is a local transport credential, not a model-provider key."
            raise GatewayError(str(detail), status=exc.code) from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise GatewayError(f"Cannot reach the local gateway at {self.api_base}: {reason}. Start it with ./start.sh or .\\start.ps1.") from exc
