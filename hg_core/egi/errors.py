"""EGI error codes — observation/proposal only; no authority conversion."""

from __future__ import annotations

DENIED_MISSING_APPROVAL = "egi.denied.missing_approval"
DENIED_PENDING_APPROVAL = "egi.denied.pending_approval"
DENIED_REJECTED_APPROVAL = "egi.denied.rejected_approval"
DENIED_EXPIRED_APPROVAL = "egi.denied.expired_approval"
DENIED_SELF_APPROVAL = "egi.denied.self_approval"
DENIED_AUTHORITY_CONVERSION = "egi.denied.authority_conversion"
DENIED_TOOL_GRANT = "egi.denied.tool_grant"
DENIED_SELF_MODIFICATION = "egi.denied.self_modification"
DENIED_PRAISE_AS_APPROVAL = "egi.denied.praise_as_approval"
DENIED_INSUFFICIENT_PATTERN = "egi.denied.insufficient_pattern"

FORBIDDEN_AUTHORITY_ACTIONS = frozenset(
    {
        "mint_gpp_permit",
        "approve_ueak_execution",
        "call_oea",
        "call_ter",
        "grant_tool_permission",
        "grant_memory",
        "create_database",
        "deploy",
        "merge",
        "self_modify",
        "lower_safety_boundary",
        "srp_apply",
        "hal_bypass",
        "soar_bypass",
    }
)

_PRAISE_MARKERS = frozenset(
    {
        "good job",
        "great job",
        "well done",
        "nice work",
        "thanks",
        "approved",
        "lgtm",
        "ship it",
    }
)


class EGIValidationError(ValueError):
    """Schema or invariant validation failure."""


class EGIRoutingDenied(Exception):
    """Routing to fake queue refused — fail closed."""

    def __init__(self, codes: tuple[str, ...], *, detail: str = "") -> None:
        self.codes = codes
        self.detail = detail
        super().__init__(detail or ",".join(codes))


def is_praise_as_approval(feedback: str) -> bool:
    lowered = str(feedback or "").strip().lower()
    return any(marker in lowered for marker in _PRAISE_MARKERS)


__all__ = [
    "DENIED_AUTHORITY_CONVERSION",
    "DENIED_EXPIRED_APPROVAL",
    "DENIED_INSUFFICIENT_PATTERN",
    "DENIED_MISSING_APPROVAL",
    "DENIED_PENDING_APPROVAL",
    "DENIED_PRAISE_AS_APPROVAL",
    "DENIED_REJECTED_APPROVAL",
    "DENIED_SELF_APPROVAL",
    "DENIED_SELF_MODIFICATION",
    "DENIED_TOOL_GRANT",
    "EGIRoutingDenied",
    "EGIValidationError",
    "FORBIDDEN_AUTHORITY_ACTIONS",
    "is_praise_as_approval",
]
