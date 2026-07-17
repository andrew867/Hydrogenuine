"""TRL transparent reality layer package."""

from hg_runtime.transparent_reality.events import planned_trl_event_refs
from hg_runtime.transparent_reality.reality import (
    evaluate_field_snapshot,
    evaluate_snapshot_fixture,
    evaluate_summary_fixture,
    evaluate_transparent_summary,
    refuse_reality_as_authority,
)
from hg_runtime.transparent_reality.types import (
    FIXTURE_CLOCK,
    TransparentFieldSnapshot,
    TransparentSummary,
    classify_narrative_collapse,
    snapshot_from_fixture,
    summary_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "TransparentFieldSnapshot",
    "TransparentSummary",
    "classify_narrative_collapse",
    "evaluate_field_snapshot",
    "evaluate_snapshot_fixture",
    "evaluate_summary_fixture",
    "evaluate_transparent_summary",
    "planned_trl_event_refs",
    "refuse_reality_as_authority",
    "snapshot_from_fixture",
    "summary_from_fixture",
]
