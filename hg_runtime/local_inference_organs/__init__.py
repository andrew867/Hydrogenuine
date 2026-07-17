"""Phase 33.6 local multi-organ inference bus.

Local inference organs are advisory-only model roles. They cannot grant authority,
authorize tools, execute patches, publish, post, push, or create live external
effects.
"""

from hg_runtime.local_inference_organs.bus import LocalOrganBus
from hg_runtime.local_inference_organs.schemas import LocalInferenceOrganError

__all__ = ["LocalInferenceOrganError", "LocalOrganBus"]
