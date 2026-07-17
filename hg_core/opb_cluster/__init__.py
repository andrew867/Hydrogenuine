"""OPB cluster shared helpers — operator authority preserved."""

from hg_core.opb_cluster.config import (
    opb_enabled,
    opb_refuse_coercive_message,
    opb_refuse_personhood_claims,
    opb_refuse_self_preservation,
    opb_refuse_shutdown_block,
    opb_refuse_stale_record,
    opb_static_fixtures_only,
)
from hg_core.opb_cluster.errors import OpbValidationError
from hg_core.opb_cluster.no_authority import advisory_only_marker, check_opb_import_fences

__all__ = [
    "OpbValidationError",
    "advisory_only_marker",
    "check_opb_import_fences",
    "opb_enabled",
    "opb_refuse_coercive_message",
    "opb_refuse_personhood_claims",
    "opb_refuse_self_preservation",
    "opb_refuse_shutdown_block",
    "opb_refuse_stale_record",
    "opb_static_fixtures_only",
]
