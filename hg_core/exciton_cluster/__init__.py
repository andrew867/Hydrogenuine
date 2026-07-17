"""EXCITON / operator product surface cluster — backburner guard."""

from hg_core.exciton_cluster.config import (
    exciton_backburner_guard,
    exciton_enabled,
    exciton_fake_dispatch_only,
    exciton_native_ui_allowed,
    exciton_refuse_authority_conversion,
    exciton_refuse_stale_approval,
    exciton_static_fixtures_only,
)
from hg_core.exciton_cluster.errors import ExcitonValidationError
from hg_core.exciton_cluster.events import planned_exciton_event_refs

__all__ = [
    "ExcitonValidationError",
    "exciton_backburner_guard",
    "exciton_enabled",
    "exciton_fake_dispatch_only",
    "exciton_native_ui_allowed",
    "exciton_refuse_authority_conversion",
    "exciton_refuse_stale_approval",
    "exciton_static_fixtures_only",
    "planned_exciton_event_refs",
]
