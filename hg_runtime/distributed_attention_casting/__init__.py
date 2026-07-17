"""DAC distributed attention casting package."""

from hg_runtime.distributed_attention_casting.casting import (
    evaluate_attention_cast,
    evaluate_cast_fixture,
    refuse_cast_as_authority,
)
from hg_runtime.distributed_attention_casting.events import planned_dac_event_refs
from hg_runtime.distributed_attention_casting.types import (
    FIXTURE_CLOCK,
    AttentionCast,
    cast_from_fixture,
    classify_cast_risk,
)

__all__ = [
    "FIXTURE_CLOCK",
    "AttentionCast",
    "cast_from_fixture",
    "classify_cast_risk",
    "evaluate_attention_cast",
    "evaluate_cast_fixture",
    "planned_dac_event_refs",
    "refuse_cast_as_authority",
]
