"""AIS-0 Agent Immune System schema foundation.

Detection is not authority. Fever restricts; never unlocks. Quarantine is not
deletion. Decay is not erasure. Security audit is defensive-only.
"""

from hg_runtime.agent_immune_system.gate import validate_ais0_gate
from hg_runtime.agent_immune_system.schemas import (
    DOCTRINE,
    PHASE_ID,
    VERDICT_GREEN,
    AISImmuneError,
)

__all__ = [
    "AISImmuneError",
    "DOCTRINE",
    "PHASE_ID",
    "VERDICT_GREEN",
    "validate_ais0_gate",
]
