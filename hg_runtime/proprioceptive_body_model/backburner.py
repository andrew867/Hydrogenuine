"""PRO backburner boundary guard — embodiment/hardware deferred."""

from __future__ import annotations

from pathlib import Path

from hg_core.runtime_context.config import pro_backburner_guard, pro_enabled, pro_hardware_allowed
from hg_core.runtime_context.errors import REFUSED_PRO_NOT_ON_BACKBURNER, RuntimeContextValidationError

PRO_PLANNING_SPEC = Path(__file__).resolve().parents[2] / "docs" / "planning" / "proprioceptive_body_model" / "PRO_SPEC.md"


def refuse_pro_off_backburner(*, allow_runtime: bool) -> None:
    if allow_runtime and pro_backburner_guard():
        raise RuntimeContextValidationError(
            REFUSED_PRO_NOT_ON_BACKBURNER,
            "PRO runtime activation refused while backburner guard is active",
        )


def assert_pro_backburner_boundary() -> dict[str, object]:
    """Confirm PRO remains backburner until embodiment/hardware requirements are real."""
    spec_text = PRO_PLANNING_SPEC.read_text(encoding="utf-8") if PRO_PLANNING_SPEC.is_file() else ""
    planning_backburner = "BACKBURNER" in spec_text
    return {
        "backburner_guard_active": pro_backburner_guard(),
        "runtime_disabled_by_default": not pro_enabled(),
        "hardware_not_allowed_by_default": not pro_hardware_allowed(),
        "planning_spec_present": PRO_PLANNING_SPEC.is_file(),
        "planning_spec_declares_backburner": planning_backburner,
        "embodiment_hardware_deferred": pro_backburner_guard() and not pro_hardware_allowed(),
    }


__all__ = ["assert_pro_backburner_boundary", "refuse_pro_off_backburner"]
