"""Minimal local provider HTTP clients — OpenAI-compatible only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

DEFAULT_TIMEOUT = 5.0


def probe_http_endpoint(endpoint: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Probe OpenAI-compatible /v1/models or root endpoint."""
    if not endpoint or not endpoint.strip():
        return {"available": False, "failure_reason": "endpoint not configured"}
    base = endpoint.rstrip("/")
    urls = [f"{base}/v1/models", f"{base}/health", base]
    last_err = "unreachable"
    for url in urls:
        try:
            req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status >= 400:
                    continue
                body = resp.read().decode("utf-8", errors="replace")
                context_length = None
                try:
                    data = json.loads(body) if body.strip().startswith("{") else {}
                    if isinstance(data.get("data"), list) and data["data"]:
                        context_length = data["data"][0].get("context_length")
                except json.JSONDecodeError:
                    data = {}
                return {
                    "available": True,
                    "endpoint": url,
                    "context_length": context_length,
                    "degraded": False,
                }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = str(exc)
            continue
    return {"available": False, "failure_reason": last_err}


def complete_openai_compatible(
    endpoint: str,
    *,
    model_id: str,
    prompt: str,
    json_mode: bool = True,
    timeout: float = 30.0,
    max_tokens: int | None = None,
    http_post: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call /v1/chat/completions on OpenAI-compatible endpoint."""
    if not endpoint:
        return {"ok": False, "failure_reason": "endpoint not configured", "output_text": ""}
    base = endpoint.rstrip("/")
    url = f"{base}/v1/chat/completions"
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    if http_post is not None:
        return http_post(url, body)

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            choices = data.get("choices") or []
            text = ""
            if choices:
                text = (choices[0].get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            return {
                "ok": True,
                "output_text": text,
                "finish_reason": choices[0].get("finish_reason") if choices else None,
                "token_counts": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
                "raw_response": raw,
            }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "failure_reason": str(exc), "output_text": ""}


def unavailable_stub_response() -> dict[str, Any]:
    """Honest unavailable response — no fake cognition text."""
    return {
        "ok": False,
        "failure_reason": "provider unavailable",
        "output_text": "",
        "unavailable": True,
    }
