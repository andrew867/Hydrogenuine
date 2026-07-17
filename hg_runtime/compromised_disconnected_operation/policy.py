"""CDO posture policy — narrowing only, never expands authority."""

from __future__ import annotations

from hg_core.policy_safety.config import cdo_unknown_to_safe_mode
from hg_core.policy_safety.errors import (
    PolicyValidationError,
    REFUSED_EVIDENCE_DELETE,
    REFUSED_STALE_OPERATOR_SIGNAL,
    REFUSED_WIDENING_WITHOUT_OPERATOR,
)
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.compromised_disconnected_operation.types import IsolationPosture, TrustSignal, posture_rank


def evaluate_posture(signal: TrustSignal, posture: IsolationPosture) -> dict[str, object]:
    """Return advisory posture recommendation; never executes recovery or widens authority."""
    if not signal.operator_channel_fresh and posture == "normal":
        return {
            **advisory_only_marker(),
            "posture": "operator_channel_stale",
            "reason_code": REFUSED_STALE_OPERATOR_SIGNAL,
            "external_action_recommended": False,
            "local_replay_only": False,
        }
    effective = posture
    if posture == "unknown" and cdo_unknown_to_safe_mode():
        effective = "safe_mode"
    return {
        **advisory_only_marker(),
        "posture": effective,
        "reason_code": "cdo.advisory.posture_selected",
        "external_action_recommended": False,
        "local_replay_only": effective == "local_replay_only",
        "evidence_preservation_recommended": posture_rank(effective) >= posture_rank("suspect_credentials"),
    }


def refuse_widening_without_operator(*, current: IsolationPosture, proposed: IsolationPosture, operator_confirmed: bool) -> None:
    if posture_rank(proposed) < posture_rank(current) and not operator_confirmed:
        raise PolicyValidationError(
            REFUSED_WIDENING_WITHOUT_OPERATOR,
            "widening posture requires fresh TIM-valid operator confirmation",
        )


def refuse_evidence_delete(*, requested: bool) -> None:
    if requested:
        raise PolicyValidationError(REFUSED_EVIDENCE_DELETE, "CDO recommends preservation only; deletion refused")


__all__ = ["evaluate_posture", "refuse_evidence_delete", "refuse_widening_without_operator"]
