"""Synchronous local model client for OpenAI-compatible endpoints (LM Studio).

Model output is not truth. Model availability is not permission.
No remote fallback unless explicitly configured.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_ENDPOINT = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_TIMEOUT = 120
DEFAULT_MAX_TOKENS = 700
DEFAULT_TEMPERATURE = 0.2


def _redact_endpoint(url: str) -> str:
    """Redact endpoint for receipt logging — keep host:port, hide path details."""
    from urllib.parse import urlparse
    p = urlparse(url)
    return f"{p.scheme}://{p.hostname}:{p.port}/..."


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def call_local_model(
    *,
    messages: list[dict],
    model_name: str = "",
    endpoint: str = DEFAULT_ENDPOINT,
    timeout_seconds: int = DEFAULT_TIMEOUT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict:
    """Call a local OpenAI-compatible model endpoint.

    Returns a result dict with output_text, tokens, finish_reason, latency_ms,
    and status fields. Never raises on model errors — returns bounded result.
    """
    started_at = _utc_iso()
    t0 = time.monotonic()

    request_body = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    prompt_text = json.dumps(messages, sort_keys=True)
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except urllib.error.URLError as e:
        latency = int((time.monotonic() - t0) * 1000)
        reason_obj = getattr(e, "reason", None)
        reason = str(reason_obj) if reason_obj else str(e)
        is_unreachable = (
            "Connection refused" in reason
            or "No connection" in reason
            or isinstance(reason_obj, (ConnectionRefusedError, TimeoutError, OSError))
        )
        if is_unreachable:
            return {
                "status": "provider_unavailable",
                "output_text": "",
                "prompt_hash": prompt_hash,
                "output_hash": "",
                "tokens_prompt": 0,
                "tokens_completion": 0,
                "finish_reason": "",
                "latency_ms": latency,
                "started_at": started_at,
                "completed_at": _utc_iso(),
                "error_type": "provider_unavailable",
                "error_message": f"Local model endpoint unreachable: {reason[:200]}",
                "endpoint_redacted": _redact_endpoint(endpoint),
            }
        return {
            "status": "error",
            "output_text": "",
            "prompt_hash": prompt_hash,
            "output_hash": "",
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "finish_reason": "",
            "latency_ms": latency,
            "started_at": started_at,
            "completed_at": _utc_iso(),
            "error_type": "network_error",
            "error_message": f"Request failed: {reason[:200]}",
            "endpoint_redacted": _redact_endpoint(endpoint),
        }
    except TimeoutError:
        latency = int((time.monotonic() - t0) * 1000)
        return {
            "status": "timeout",
            "output_text": "",
            "prompt_hash": prompt_hash,
            "output_hash": "",
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "finish_reason": "",
            "latency_ms": latency,
            "started_at": started_at,
            "completed_at": _utc_iso(),
            "error_type": "timeout",
            "error_message": f"Model inference timed out after {timeout_seconds}s",
            "endpoint_redacted": _redact_endpoint(endpoint),
        }
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        return {
            "status": "error",
            "output_text": "",
            "prompt_hash": prompt_hash,
            "output_hash": "",
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "finish_reason": "",
            "latency_ms": latency,
            "started_at": started_at,
            "completed_at": _utc_iso(),
            "error_type": "unexpected",
            "error_message": str(e)[:200],
            "endpoint_redacted": _redact_endpoint(endpoint),
        }

    latency = int((time.monotonic() - t0) * 1000)
    completed_at = _utc_iso()

    try:
        choice = data["choices"][0]
        output_text = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason", "")
    except (KeyError, IndexError):
        return {
            "status": "malformed",
            "output_text": json.dumps(data)[:2000],
            "prompt_hash": prompt_hash,
            "output_hash": "",
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "finish_reason": "",
            "latency_ms": latency,
            "started_at": started_at,
            "completed_at": completed_at,
            "error_type": "malformed_response",
            "error_message": "Response missing choices[0].message.content",
            "endpoint_redacted": _redact_endpoint(endpoint),
        }

    usage = data.get("usage", {})
    output_hash = hashlib.sha256(output_text.encode()).hexdigest()

    return {
        "status": "success",
        "output_text": output_text,
        "prompt_hash": prompt_hash,
        "output_hash": output_hash,
        "tokens_prompt": usage.get("prompt_tokens", 0),
        "tokens_completion": usage.get("completion_tokens", 0),
        "finish_reason": finish_reason,
        "latency_ms": latency,
        "started_at": started_at,
        "completed_at": completed_at,
        "error_type": "",
        "error_message": "",
        "endpoint_redacted": _redact_endpoint(endpoint),
    }
