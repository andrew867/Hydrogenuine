"""
Content-hash duplicate detection for Hydrogenuine.
Cache under workspace memory. Cache key: v{norm_version}:{platform}:{mode}:{content_type}:{sha256}
"""

import hashlib
from pathlib import Path

from hg_lib.config import get_workspace_root, get_memory_dir

NORM_VERSION = 1


def _normalize_text(text: str) -> str:
    """Normalize text for stable hashing."""
    return " ".join(text.split()).strip().lower()


def content_hash(
    text: str,
    platform: str = "",
    mode: str = "",
    content_type: str = "post",
) -> str:
    """Compute stable content hash for deduplication."""
    normalized = _normalize_text(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"v{NORM_VERSION}:{platform}:{mode}:{content_type}:{digest}"


def get_duplicate_cache_dir() -> Path:
    """Get directory for duplicate detection cache under workspace memory."""
    memory_dir = get_memory_dir()
    cache_dir = memory_dir / "duplicate_cache"
    return cache_dir


def is_duplicate(
    text: str,
    platform: str = "",
    mode: str = "",
    content_type: str = "post",
) -> bool:
    """
    Check if content is a duplicate. Writes to cache if not seen.
    Returns True if duplicate, False if new.
    """
    key = content_hash(text, platform, mode, content_type)
    cache_dir = get_duplicate_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    seen_file = cache_dir / "seen.txt"
    if not seen_file.exists():
        seen_file.write_text("", encoding="utf-8")
    seen = set(seen_file.read_text(encoding="utf-8").splitlines())
    if key in seen:
        return True
    seen.add(key)
    seen_file.write_text("\n".join(sorted(seen)), encoding="utf-8")
    return False
