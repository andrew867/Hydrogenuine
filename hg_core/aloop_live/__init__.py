"""ALOOP-LIVE cluster — governed autonomous loop supervisor proof gates."""

from hg_core.aloop_live.config import (
    aloop_fake_sink_only,
    aloop_refuse_authority_conversion,
    aloop_refuse_live_loop_start,
    aloop_refuse_self_renewal,
)
from hg_core.aloop_live.errors import AloopValidationError
from hg_core.aloop_live.no_authority import advisory_only_marker, check_aloop_import_fences

__all__ = [
    "AloopValidationError",
    "advisory_only_marker",
    "aloop_fake_sink_only",
    "aloop_refuse_authority_conversion",
    "aloop_refuse_live_loop_start",
    "aloop_refuse_self_renewal",
    "check_aloop_import_fences",
]
