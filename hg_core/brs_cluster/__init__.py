"""BRS cluster — Bus Rate Supervisor is not authority."""

from hg_core.brs_cluster.config import (
    brs_enabled,
    brs_refuse_authority_conversion,
    brs_refuse_live_model_invocation,
    brs_static_fixtures_only,
)
from hg_core.brs_cluster.errors import BrsValidationError
from hg_core.brs_cluster.events import planned_brs_event_refs

__all__ = [
    "BrsValidationError",
    "brs_enabled",
    "brs_refuse_authority_conversion",
    "brs_refuse_live_model_invocation",
    "brs_static_fixtures_only",
    "planned_brs_event_refs",
]
