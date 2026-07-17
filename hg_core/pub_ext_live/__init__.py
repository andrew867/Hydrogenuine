"""PUB-EXT-LIVE cluster — governed live publication external action proof gates."""

from hg_core.pub_ext_live.config import (
    pub_ext_fake_sink_only,
    pub_ext_refuse_authority_conversion,
    pub_ext_refuse_live_external_action,
)
from hg_core.pub_ext_live.errors import PubExtValidationError
from hg_core.pub_ext_live.no_authority import advisory_only_marker, check_pub_ext_import_fences

__all__ = [
    "PubExtValidationError",
    "advisory_only_marker",
    "check_pub_ext_import_fences",
    "pub_ext_fake_sink_only",
    "pub_ext_refuse_authority_conversion",
    "pub_ext_refuse_live_external_action",
]
