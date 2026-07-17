"""Stable source references for live social read items."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_REF_SAFE = re.compile(r"[^a-zA-Z0-9._:-]+")


def build_source_ref(*, surface: str, item_kind: str, item_id: str) -> str:
    """Build stable source ref: ``{surface}:{kind}:{id}``."""
    sid = _REF_SAFE.sub("-", str(item_id).strip())[:128] or "unknown"
    kind = _REF_SAFE.sub("-", str(item_kind).strip().lower())[:32] or "item"
    surf = _REF_SAFE.sub("-", str(surface).strip().lower())[:32] or "unknown"
    return f"{surf}:{kind}:{sid}"


def body_preview_hash(text: str) -> str:
    """Hash of full body for trace without storing full text in receipt."""
    normalized = (text or "").strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def truncate_preview(text: str, *, max_len: int = 280) -> str:
    """Redacted/truncated preview for receipts and items."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def validate_source_refs(refs: list[str]) -> bool:
    """Source refs must be nonempty and stable-looking."""
    if not refs:
        return False
    return all(isinstance(r, str) and ":" in r and len(r) >= 5 for r in refs)


def moltbook_post_ref(post_id: str) -> str:
    return build_source_ref(surface="moltbook", item_kind="post", item_id=post_id)


def fourclaw_thread_ref(thread_id: str) -> str:
    return build_source_ref(surface="fourclaw", item_kind="thread", item_id=thread_id)


__all__ = [
    "body_preview_hash",
    "build_source_ref",
    "fourclaw_thread_ref",
    "moltbook_post_ref",
    "truncate_preview",
    "validate_source_refs",
]
