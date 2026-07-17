"""Redaction policy — no secrets, raw prompts, or hidden chain-of-thought by default."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from hg_runtime.openvino_watchtower.schema import TelemetryRedactionPolicy

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|cookie|private[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
)

_COT_KEYS = frozenset(
    {
        "chain_of_thought",
        "cot",
        "hidden_reasoning",
        "scratchpad",
        "internal_monologue",
    }
)

_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "password",
        "token",
        "bearer",
        "cookie",
        "session_token",
        "private_key",
        "credentials",
        "raw_prompt",
        "raw_completion",
        "raw_system_prompt",
    }
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_text(text: str, *, policy: TelemetryRedactionPolicy | None = None) -> str:
    policy = policy or TelemetryRedactionPolicy()
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    if not policy.raw_prompts_enabled and not policy.raw_completions_enabled:
        if policy.dev_preview_chars > 0 and len(out) > policy.dev_preview_chars:
            return out[: policy.dev_preview_chars] + "…[redacted]"
        if len(out) > 0 and policy.show_hashes:
            return f"sha256:{_sha256(out)} len={len(out)}"
    return out


def redact_payload(obj: Any, *, policy: TelemetryRedactionPolicy | None = None) -> tuple[Any, list[str]]:
    """Return redacted copy and list of redaction actions applied."""
    policy = policy or TelemetryRedactionPolicy()
    applied: list[str] = []

    def walk(value: Any, path: str) -> Any:
        if isinstance(value, dict):
            clean: dict[str, Any] = {}
            for k, v in value.items():
                low = str(k).lower()
                if low in _FORBIDDEN_KEYS or any(f in low for f in _FORBIDDEN_KEYS):
                    applied.append(f"removed_key:{path}/{k}")
                    if policy.show_hashes and isinstance(v, str):
                        clean[k + "_hash"] = _sha256(v)
                        clean[k + "_length"] = len(v)
                    continue
                if not policy.hidden_chain_of_thought_enabled and low in _COT_KEYS:
                    applied.append(f"removed_cot:{path}/{k}")
                    continue
                if low in {"prompt", "completion", "output", "input"} and not policy.raw_prompts_enabled:
                    if isinstance(v, str):
                        applied.append(f"redacted_text:{path}/{k}")
                        clean[k + "_hash"] = _sha256(v)
                        clean[k + "_length"] = len(v)
                        if policy.dev_preview_chars > 0:
                            clean[k + "_preview"] = redact_text(v, policy=policy)
                        continue
                clean[k] = walk(v, f"{path}/{k}")
            return clean
        if isinstance(value, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(value)]
        return value

    return walk(obj, ""), applied


__all__ = ["redact_payload", "redact_text"]
