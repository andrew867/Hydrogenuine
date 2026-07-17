"""Admission ingress helpers for mutation entry points (CT-06 ADM)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from hg_core.admission.types import AdmissionDecision, AdmissionRequest, AdmissionToken, ApprovalBinding

if TYPE_CHECKING:
    from hg_core.admission.controller import AdmissionController

_default_controller: "AdmissionController | None" = None


def get_controller() -> "AdmissionController":
    global _default_controller
    if _default_controller is None:
        from hg_core.admission.controller import AdmissionController

        _default_controller = AdmissionController()
    return _default_controller


def reset_controller() -> None:
    global _default_controller
    _default_controller = None


def require_admission(req: AdmissionRequest) -> AdmissionDecision:
    """Acquire admission before mutating shared state — fail closed on refusal."""
    return get_controller().request(req)


@contextmanager
def admission_scope(req: AdmissionRequest) -> Iterator[AdmissionToken]:
    decision = require_admission(req)
    if not decision.admitted or decision.token is None:
        raise AdmissionRefused(decision.reason_code, decision)
    try:
        yield decision.token
    finally:
        get_controller().release(decision.token)


class AdmissionRefused(Exception):
    def __init__(self, reason_code: str, decision: AdmissionDecision) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.decision = decision


def map_srp_apply_reason(reason_code: str) -> str:
    """Map admission refusal to SRP-facing reason where applicable."""
    if reason_code.startswith("admission."):
        return reason_code
    return reason_code


__all__ = [
    "AdmissionRefused",
    "ApprovalBinding",
    "admission_scope",
    "get_controller",
    "map_srp_apply_reason",
    "require_admission",
    "reset_controller",
]
