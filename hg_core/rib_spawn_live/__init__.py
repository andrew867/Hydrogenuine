"""RIB-SPAWN-LIVE cluster — governed reproduction spawn proof gates."""

from hg_core.rib_spawn_live.config import (
    rib_spawn_fake_sink_only,
    rib_spawn_refuse_authority_conversion,
    rib_spawn_refuse_inherited_authority,
    rib_spawn_refuse_live_spawn,
)
from hg_core.rib_spawn_live.errors import RibSpawnValidationError
from hg_core.rib_spawn_live.no_authority import advisory_only_marker, check_rib_spawn_import_fences

__all__ = [
    "RibSpawnValidationError",
    "advisory_only_marker",
    "check_rib_spawn_import_fences",
    "rib_spawn_fake_sink_only",
    "rib_spawn_refuse_authority_conversion",
    "rib_spawn_refuse_inherited_authority",
    "rib_spawn_refuse_live_spawn",
]
