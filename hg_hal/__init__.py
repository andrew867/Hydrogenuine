"""HAL — Hierarchical Arbitration Loop runtime."""

from hg_hal.arbitration import arbitrate, decision_ref_for_result, hal_enabled
from hg_hal.event_log import HalEventLogAdapter
from hg_hal.models import (
    HalArbitrationContext,
    HalDecision,
    HalDecisionReason,
    HalEvent,
    HalRequest,
    HalRoute,
    HalRuntimeState,
    fixture_hal_request,
)
from hg_hal.reducer import HalReducer
from hg_hal.replay import HalReplayVerifier, verify_replay
from hg_hal.rtc_bridge import arbitration_recorded_draft, arbitration_requested_draft
from hg_hal.runtime import HalRuntime
from hg_hal.types import (
    ArbitrationCandidate,
    ArbitrationRequest,
    ArbitrationResult,
    request_from_proposal,
)

__all__ = [
    "ArbitrationCandidate",
    "ArbitrationRequest",
    "ArbitrationResult",
    "HalArbitrationContext",
    "HalDecision",
    "HalDecisionReason",
    "HalEvent",
    "HalEventLogAdapter",
    "HalReducer",
    "HalReplayVerifier",
    "HalRequest",
    "HalRoute",
    "HalRuntime",
    "HalRuntimeState",
    "arbitrate",
    "arbitration_recorded_draft",
    "arbitration_requested_draft",
    "decision_ref_for_result",
    "fixture_hal_request",
    "hal_enabled",
    "request_from_proposal",
    "verify_replay",
]
