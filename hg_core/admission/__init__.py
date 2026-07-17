"""Admission / concurrency control (CT-06 ADM)."""

from hg_core.admission.ingress import (
    AdmissionRefused,
    admission_scope,
    get_controller,
    require_admission,
    reset_controller,
)
from hg_core.admission.types import AdmissionDecision, AdmissionRequest, AdmissionToken, ApprovalBinding


def __getattr__(name: str):
    if name == "AdmissionController":
        from hg_core.admission.controller import AdmissionController

        return AdmissionController
    raise AttributeError(name)


__all__ = [
    "AdmissionController",
    "AdmissionDecision",
    "AdmissionRefused",
    "AdmissionRequest",
    "AdmissionToken",
    "ApprovalBinding",
    "admission_scope",
    "get_controller",
    "require_admission",
    "reset_controller",
]
