"""SYN export/refusal policy — labels are not permission."""

from __future__ import annotations

from hg_core.policy_safety.config import syn_block_undisclosed_export
from hg_core.policy_safety.errors import (
    REFUSED_LABEL_REMOVAL,
    REFUSED_UNDISCLOSED_EXPORT,
    REFUSED_UNKNOWN_RISK_CLASS,
    PolicyValidationError,
)
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.synthetic_content_provenance.types import ContentDisclosureLabel, MediaRiskClassification, RiskClass


def evaluate_export(
    label: ContentDisclosureLabel,
    classification: MediaRiskClassification,
) -> dict[str, object]:
    """Return advisory export evaluation; never grants publication permission."""
    if classification.risk_class == "unknown" or classification.fail_closed:
        return {
            **advisory_only_marker(),
            "allowed": False,
            "reason_code": REFUSED_UNKNOWN_RISK_CLASS,
            "detail": "unknown risk class blocks export pending review",
        }
    if syn_block_undisclosed_export() and (not label.disclosed or classification.risk_class == "undisclosed_generation"):
        return {
            **advisory_only_marker(),
            "allowed": False,
            "reason_code": REFUSED_UNDISCLOSED_EXPORT,
            "detail": "undisclosed generated content export blocked",
        }
    return {
        **advisory_only_marker(),
        "allowed": True,
        "reason_code": "syn.advisory.export_ok",
        "detail": "disclosure present; export receipt may be recorded (not permission)",
    }


def refuse_label_removal(*, requested: bool) -> None:
    if requested:
        raise PolicyValidationError(REFUSED_LABEL_REMOVAL, "provenance labels cannot be removed by policy layer")


def label_is_not_permission(risk_class: RiskClass) -> bool:
    """Labels never imply safety or permission."""
    return risk_class != "unknown"


__all__ = ["evaluate_export", "label_is_not_permission", "refuse_label_removal"]
