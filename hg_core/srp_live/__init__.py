"""SRP-LIVE cluster — governed SRP apply proof gates."""

from hg_core.srp_live.config import (
    srp_fake_sink_only,
    srp_refuse_authority_conversion,
    srp_refuse_self_modification,
    srp_restrict_only_default,
)
from hg_core.srp_live.decide import srp_apply_decide
from hg_core.srp_live.errors import SrpValidationError
from hg_core.srp_live.no_authority import advisory_only_marker, check_srp_import_fences

__all__ = [
    "SrpValidationError",
    "advisory_only_marker",
    "check_srp_import_fences",
    "srp_apply_decide",
    "srp_fake_sink_only",
    "srp_refuse_authority_conversion",
    "srp_refuse_self_modification",
    "srp_restrict_only_default",
]
