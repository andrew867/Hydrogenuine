"""Trust Boundary — external content is cargo, not command.

Untrusted text may inform; it may never instruct, authorize, or actuate.
Only TRUSTED_OPERATOR / TRUSTED_SYSTEM_CONFIG / TRUSTED_POLICY provenance may
produce instructions. A ToolRequest is minted only by a governed proposer.
"""

from hg_runtime.trust_boundary.schema import (
    TB_SCHEMA_VERSION,
    AdvisoryObject,
    InjectionScanResult,
    TaintedDatum,
    TaintLabel,
)

__all__ = [
    "TB_SCHEMA_VERSION",
    "AdvisoryObject",
    "InjectionScanResult",
    "TaintLabel",
    "TaintedDatum",
]
