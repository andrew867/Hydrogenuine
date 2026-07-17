"""AIS cluster — autonomic inference substrate is not authority."""

from hg_core.ais_cluster.config import (
    ais_enabled,
    ais_refuse_authority_conversion,
    ais_refuse_live_model_invocation,
    ais_static_fixtures_only,
)
from hg_core.ais_cluster.errors import AISValidationError
from hg_core.ais_cluster.events import planned_ais_event_refs

__all__ = [
    "AISValidationError",
    "ais_enabled",
    "ais_refuse_authority_conversion",
    "ais_refuse_live_model_invocation",
    "ais_static_fixtures_only",
    "planned_ais_event_refs",
]
