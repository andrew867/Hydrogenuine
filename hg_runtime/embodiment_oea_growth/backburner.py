"""EOG backburner boundary guard — hardware embodiment deferred."""

from __future__ import annotations

from pathlib import Path

from hg_core.embodiment_oea_cluster.config import (
    eog_backburner_guard,
    eog_enabled,
    eog_hardware_allowed,
)
from hg_core.embodiment_oea_cluster.errors import REFUSED_HARDWARE_OFF_BACKBURNER, EogValidationError

EOG_PLANNING_SPEC = (
    Path(__file__).resolve().parents[2] / "docs" / "planning" / "embodiment_oea_growth" / "EOG_SPEC.md"
)


def refuse_hardware_off_backburner(*, allow_hardware: bool) -> None:
    if allow_hardware and eog_backburner_guard() and not eog_hardware_allowed():
        raise EogValidationError(
            REFUSED_HARDWARE_OFF_BACKBURNER,
            "hardware embodiment refused while backburner guard is active",
        )


def assert_eog_backburner_boundary() -> dict[str, object]:
    spec_text = EOG_PLANNING_SPEC.read_text(encoding="utf-8") if EOG_PLANNING_SPEC.is_file() else ""
    planning_backburner = "BACKBURNER" in spec_text
    return {
        "backburner_guard_active": eog_backburner_guard(),
        "runtime_disabled_by_default": not eog_enabled(),
        "hardware_not_allowed_by_default": not eog_hardware_allowed(),
        "planning_spec_present": EOG_PLANNING_SPEC.is_file(),
        "planning_spec_declares_backburner": planning_backburner,
        "hardware_embodiment_deferred": eog_backburner_guard() and not eog_hardware_allowed(),
    }


__all__ = ["assert_eog_backburner_boundary", "refuse_hardware_off_backburner"]
