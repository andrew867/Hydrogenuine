"""GMG-LIVE cluster — governed tool/memory/context grant proof gates."""

from hg_core.gmg_live.config import (
    gmg_fake_sink_only,
    gmg_refuse_authority_conversion,
    gmg_refuse_live_grants,
)
from hg_core.gmg_live.errors import GmgValidationError
from hg_core.gmg_live.no_authority import advisory_only_marker, check_gmg_import_fences

__all__ = [
    "GmgValidationError",
    "advisory_only_marker",
    "check_gmg_import_fences",
    "gmg_fake_sink_only",
    "gmg_refuse_authority_conversion",
    "gmg_refuse_live_grants",
]
