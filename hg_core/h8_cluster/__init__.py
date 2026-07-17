"""H8 cluster — organism coherence is not authority."""

from hg_core.h8_cluster.config import (
    h8_enabled,
    h8_refuse_authority_conversion,
    h8_refuse_live_model_invocation,
    h8_static_fixtures_only,
)
from hg_core.h8_cluster.errors import H8ValidationError
from hg_core.h8_cluster.events import planned_h8_event_refs

__all__ = [
    "H8ValidationError",
    "h8_enabled",
    "h8_refuse_authority_conversion",
    "h8_refuse_live_model_invocation",
    "h8_static_fixtures_only",
    "planned_h8_event_refs",
]
