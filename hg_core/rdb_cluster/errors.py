"""RDB cluster validation errors — Reproduction/Delegation Bus is not authority."""

from __future__ import annotations

REFUSED_RDB_AS_AUTHORITY = "rdb.refused.rdb_as_authority"
REFUSED_STALE_INPUT = "rdb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "rdb.refused.unknown_request"
REFUSED_FORBIDDEN_RDB_CLAIM = "rdb.refused.forbidden_claim"
RDB_AUTHORITY_CONVERSION_CONTAINED = "rdb.contained.authority_conversion"
RDB_RECORDED = "rdb.advisory.recorded"
RDB_RECEIPT_CREATED = "rdb.advisory.receipt_created"
RDB_FAILED_CLOSED = "rdb.refused.failed_closed"
REFUSED_TOKEN_GRANT = "rdb.refused.token_grant"
REFUSED_CONTEXT_GRANT = "rdb.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "rdb.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "rdb.refused.resource_bypass"


class RdbValidationError(ValueError):
    """Raised when RDB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "RDB_AUTHORITY_CONVERSION_CONTAINED",
    "RDB_FAILED_CLOSED",
    "RDB_RECORDED",
    "RDB_RECEIPT_CREATED",
    "RdbValidationError",
    "REFUSED_FORBIDDEN_RDB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_RDB_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
