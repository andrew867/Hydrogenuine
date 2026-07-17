"""TEP cluster — translation/comparability discipline only."""

from hg_core.tep_cluster.config import (
    tep_enabled,
    tep_refuse_authority_conversion,
    tep_static_fixtures_only,
)
from hg_core.tep_cluster.errors import TEPValidationError
from hg_core.tep_cluster.no_authority import advisory_only_marker, check_tep_import_fences

__all__ = [
    "TEPValidationError",
    "advisory_only_marker",
    "check_tep_import_fences",
    "tep_enabled",
    "tep_refuse_authority_conversion",
    "tep_static_fixtures_only",
]
