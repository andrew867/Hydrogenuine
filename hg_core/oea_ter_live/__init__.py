"""OEA-TER-LIVE cluster — governed live OEA/TER bridge proof gates."""

from hg_core.oea_ter_live.config import (
    oea_ter_fake_sink_only,
    oea_ter_refuse_authority_conversion,
    oea_ter_refuse_live_actions,
)
from hg_core.oea_ter_live.errors import OeaTerValidationError
from hg_core.oea_ter_live.no_authority import advisory_only_marker, check_oea_ter_import_fences

__all__ = [
    "OeaTerValidationError",
    "advisory_only_marker",
    "check_oea_ter_import_fences",
    "oea_ter_fake_sink_only",
    "oea_ter_refuse_authority_conversion",
    "oea_ter_refuse_live_actions",
]
