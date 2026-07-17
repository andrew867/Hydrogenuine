"""WMBR-06 / CAGI-47 world-model audit, decay, and retraction closure.

Consumes WMBR-05 predictive calibration artifacts and produces a deterministic
audit/maintenance layer. Decay is not deletion. Retraction is not erasure.
Audit closure is not laundering.
"""

from hg_runtime.world_model_audit.artifact_writer import build_audit_layer, secret_scan
from hg_runtime.world_model_audit.gate import validate_wmbr06_gate
from hg_runtime.world_model_audit.schemas import (
    DOCTRINE,
    PHASE_ID,
    VERDICT_GREEN,
    WorldModelAuditError,
)

__all__ = [
    "DOCTRINE",
    "PHASE_ID",
    "VERDICT_GREEN",
    "WorldModelAuditError",
    "build_audit_layer",
    "secret_scan",
    "validate_wmbr06_gate",
]
