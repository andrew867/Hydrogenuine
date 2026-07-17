"""RTC cognition service — proposal-only streaming adapters."""

from hg_runtime.cognition.config import (
    CognitionConfig,
    LiveCognitionConfigError,
    load_cognition_config,
    validate_live_config,
)
from hg_runtime.cognition.fake_provider import FakeModelProvider
from hg_runtime.cognition.handler import StreamingCognitionHandler
from hg_runtime.cognition.provider import ModelProvider, build_provider
from hg_runtime.cognition.replay import find_recorded_proposal, reconstruct_assembled_text
from hg_runtime.cognition.streaming import COGNITION_DECISION_PROPOSAL_TYPES, stream_proposal_drafts

__all__ = [
    "COGNITION_DECISION_PROPOSAL_TYPES",
    "CognitionConfig",
    "LiveCognitionConfigError",
    "FakeModelProvider",
    "ModelProvider",
    "StreamingCognitionHandler",
    "build_provider",
    "find_recorded_proposal",
    "load_cognition_config",
    "validate_live_config",
    "reconstruct_assembled_text",
    "stream_proposal_drafts",
]
