"""
Pack4: Sanitize text for RAG (untrusted facts) and memory write path.
Used to reduce injection risk when retrieved context or stored memory is shown to the model.
"""

from __future__ import annotations

from typing import Optional

from hg_core.security.prompt_injection import assess, _safe_rewrite


def sanitize_for_rag(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize retrieved text before using as RAG context.
    If assessment score is high, returns safe_rewrite or redacted snippet; otherwise returns text as-is (optionally truncated).
    """
    if not text:
        return ""
    a = assess(text)
    if a.recommended_action == "block" and a.safe_rewrite is not None:
        out = a.safe_rewrite
    elif a.score >= 70:
        out = a.safe_rewrite or _safe_rewrite(text)
    else:
        out = text
    if max_length is not None and len(out) > max_length:
        out = out[:max_length] + "..."
    return out


def sanitize_for_memory_write(text: str) -> tuple[str, bool]:
    """
    Sanitize text before writing to memory. Returns (sanitized_text, was_modified).
    If injection indicators found, returns safe_rewrite and True; else original and False.
    """
    if not text:
        return "", False
    a = assess(text)
    if a.recommended_action == "block" and a.safe_rewrite is not None:
        return a.safe_rewrite, True
    if a.score >= 70:
        return a.safe_rewrite or _safe_rewrite(text), True
    return text, False
