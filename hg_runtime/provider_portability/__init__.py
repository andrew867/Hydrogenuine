"""Phase 42 provider portability and cross-model receipt substrate."""

from hg_runtime.provider_portability.cross_model_run import run_cross_model
from hg_runtime.provider_portability.gate import validate_phase42_gate

__all__ = ["run_cross_model", "validate_phase42_gate"]
