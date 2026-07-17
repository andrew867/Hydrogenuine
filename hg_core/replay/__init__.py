"""
OS Post-Phase 5: Versioned materializers and replay compatibility.
"""

from .version_resolver import (
    register_materializer_version,
    record_materializer_run,
    publish_replay_compat_profile,
    resolve_versions_for_replay,
    load_materializer_registry,
)

__all__ = [
    "register_materializer_version",
    "record_materializer_run",
    "publish_replay_compat_profile",
    "resolve_versions_for_replay",
    "load_materializer_registry",
]
