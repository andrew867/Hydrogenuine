"""Local Evidence Bridge.

Evidence receipts are not truth. Operator-provided files are not trusted by
default. This package starts fixture-only and local-only.
"""

from hg_runtime.local_evidence_bridge.gate import validate_leb0_gate
from hg_runtime.local_evidence_bridge.schemas import VERDICT_GREEN

__all__ = ["VERDICT_GREEN", "validate_leb0_gate"]
