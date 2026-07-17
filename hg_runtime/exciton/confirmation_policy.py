"""Risk-calibrated confirmation policy for operator actions."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ConfirmationLevel(str, Enum):
    ONE_CLICK = "one_click"
    SIMPLE_CONFIRM = "simple_confirm"
    TYPE_PHRASE = "type_phrase"
    DENIED = "denied"


FORBIDDEN_CONTROLS = frozenset({
    "APPROVE_ALL", "DIRECT_PUBLISH", "DIRECT_WEB_SUBMIT", "DIRECT_LOGIN", "DIRECT_PURCHASE",
})


def confirmation_for_control(control_id: str, *, risk_class: str = "read_only") -> dict[str, Any]:
    cid = control_id.upper()
    if cid in FORBIDDEN_CONTROLS:
        return {
            "level": ConfirmationLevel.DENIED.value,
            "phrase": None,
            "human_message": "Forbidden control",
            "pressure_to_approve": False,
        }
    if risk_class in ("read_only", "status_refresh", "proof_open"):
        return {"level": ConfirmationLevel.ONE_CLICK.value, "phrase": None, "pressure_to_approve": False}
    if risk_class in ("draft", "operator_note"):
        return {"level": ConfirmationLevel.SIMPLE_CONFIRM.value, "phrase": None, "pressure_to_approve": False}
    if risk_class in ("external_write", "social_post", "medium"):
        return {
            "level": ConfirmationLevel.TYPE_PHRASE.value,
            "phrase": "APPROVE EXTERNAL WRITE",
            "pressure_to_approve": False,
        }
    if risk_class in ("high", "shell_command", "financial"):
        return {"level": ConfirmationLevel.DENIED.value, "phrase": None, "pressure_to_approve": False}
    return {"level": ConfirmationLevel.SIMPLE_CONFIRM.value, "phrase": None, "pressure_to_approve": False}


__all__ = ["ConfirmationLevel", "confirmation_for_control"]
