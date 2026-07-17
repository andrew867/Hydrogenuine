"""Console redaction — no secrets, raw prompts, or hidden CoT."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|cookie)\s*[:=]\s*\S+"),
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
)

_COT_KEYS = frozenset({"chain_of_thought", "cot", "hidden_reasoning", "scratchpad", "internal_monologue"})
_FORBIDDEN_KEYS = frozenset({"api_key", "secret", "password", "token", "raw_prompt", "raw_system_prompt"})


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_text(text: str, *, preview_chars: int = 120) -> str:
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    if len(out) > preview_chars:
        return out[:preview_chars] + "…"
    return out


def redact_payload(obj: Any) -> tuple[Any, list[str]]:
    applied: list[str] = []

    def walk(value: Any, path: str) -> Any:
        if isinstance(value, dict):
            clean: dict[str, Any] = {}
            for k, v in value.items():
                low = str(k).lower()
                if low in _FORBIDDEN_KEYS or low in _COT_KEYS:
                    applied.append(f"removed:{path}/{k}")
                    if isinstance(v, str):
                        clean[f"{k}_hash"] = sha256(v)
                    continue
                if low in {"prompt", "body", "text", "message"} and isinstance(v, str):
                    applied.append(f"redacted:{path}/{k}")
                    clean[f"{k}_preview"] = redact_text(v)
                    clean[f"{k}_hash"] = sha256(v)
                    continue
                clean[k] = walk(v, f"{path}/{k}")
            return clean
        if isinstance(value, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(value)]
        return value

    return walk(obj, ""), applied


__all__ = ["redact_payload", "redact_text", "sha256"]
