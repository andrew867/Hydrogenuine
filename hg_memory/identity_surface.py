"""
Hydrogenuine Memory identity surface (Phase D).

Callers import from hg_memory; this module imports from
hg_memory.identity (package) for persona_integration.
See docs/specs/hg_memory_api_spec.md.
"""

from pathlib import Path
from typing import Optional

try:
    from hg_memory.identity.persona_integration import (
        record_persona_update_async as _record_persona_update_async,
    )
    _IDENTITY_AVAILABLE = True
except ImportError:
    _IDENTITY_AVAILABLE = False
    _record_persona_update_async = None  # type: ignore


def record_persona_update_async(
    platform: str,
    persona_set: str,
    file_name: str,
    file_path: Path,
    before_content: Optional[str] = None,
    after_content: Optional[str] = None,
) -> None:
    """Record a persona file update in the identity graph (async)."""
    if not _IDENTITY_AVAILABLE or _record_persona_update_async is None:
        return
    _record_persona_update_async(
        platform=platform,
        persona_set=persona_set,
        file_name=file_name,
        file_path=file_path,
        before_content=before_content,
        after_content=after_content,
    )


__all__ = ["record_persona_update_async"]
