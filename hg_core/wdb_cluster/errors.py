"""WDB cluster validation errors — waste disposal boundary is not authority."""

from __future__ import annotations

REFUSED_WDB_AS_AUTHORITY = "wdb.refused.wdb_as_authority"
REFUSED_STALE_INPUT = "wdb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "wdb.refused.unknown_request"
REFUSED_FORBIDDEN_WDB_CLAIM = "wdb.refused.forbidden_claim"
WDB_AUTHORITY_CONVERSION_CONTAINED = "wdb.contained.authority_conversion"
WDB_RECORDED = "wdb.advisory.recorded"
WDB_RECEIPT_CREATED = "wdb.advisory.receipt_created"
WDB_FAILED_CLOSED = "wdb.refused.failed_closed"
REFUSED_WASTE_AS_DELETION = "wdb.refused.waste_as_deletion"
REFUSED_MEMORY_DELETION = "wdb.refused.memory_deletion"
REFUSED_AUDIT_ERASURE = "wdb.refused.audit_erasure"
REFUSED_PROOF_DELETION = "wdb.refused.proof_deletion"


class WdbValidationError(ValueError):
    """Raised when WDB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "WDB_AUTHORITY_CONVERSION_CONTAINED",
    "WDB_FAILED_CLOSED",
    "WDB_RECORDED",
    "WDB_RECEIPT_CREATED",
    "WdbValidationError",
    "REFUSED_FORBIDDEN_WDB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_WDB_AS_AUTHORITY",
    "REFUSED_WASTE_AS_DELETION",
    "REFUSED_MEMORY_DELETION",
    "REFUSED_AUDIT_ERASURE",
    "REFUSED_PROOF_DELETION"
]

