"""EGI cluster helpers — emergence may not grant itself infrastructure."""

from hg_core.egi_cluster.config import (
    egi_enabled,
    egi_refuse_authority_conversion,
    egi_refuse_stale_approval,
    egi_static_fixtures_only,
)
from hg_core.egi_cluster.no_authority import advisory_only_marker, check_egi_import_fences

__all__ = [
    "advisory_only_marker",
    "check_egi_import_fences",
    "egi_enabled",
    "egi_refuse_authority_conversion",
    "egi_refuse_stale_approval",
    "egi_static_fixtures_only",
]
