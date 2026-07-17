"""Lifecycle shared helpers — wake, rest, reset boundaries."""

from hg_core.lifecycle.config import (
    cnt_enabled,
    cnt_refuse_identity_continuity,
    cnt_refuse_stale_authority_inheritance,
    cnt_static_fixtures_only,
    crr_alignment_enabled,
    crr_forbid_process_kill,
    crr_forbid_successor_spawn,
    crr_refuse_stale_alignment,
    crr_static_fixtures_only,
    mor_enabled,
    mor_forbid_process_kill,
    mor_forbid_successor_spawn,
    mor_refuse_stale_death_notice,
    mor_static_fixtures_only,
)
from hg_core.lifecycle.errors import LifecycleValidationError
from hg_core.lifecycle.no_authority import advisory_only_marker, check_lifecycle_import_fences

__all__ = [
    "LifecycleValidationError",
    "advisory_only_marker",
    "check_lifecycle_import_fences",
    "cnt_enabled",
    "cnt_refuse_identity_continuity",
    "cnt_refuse_stale_authority_inheritance",
    "cnt_static_fixtures_only",
    "crr_alignment_enabled",
    "crr_forbid_process_kill",
    "crr_forbid_successor_spawn",
    "crr_refuse_stale_alignment",
    "crr_static_fixtures_only",
    "mor_enabled",
    "mor_forbid_process_kill",
    "mor_forbid_successor_spawn",
    "mor_refuse_stale_death_notice",
    "mor_static_fixtures_only",
]
