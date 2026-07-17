"""EXCITON backburner boundary guard — native UI deferred."""

from __future__ import annotations

from pathlib import Path

from hg_core.exciton_cluster.config import (
    exciton_backburner_guard,
    exciton_enabled,
    exciton_native_ui_allowed,
)
from hg_core.exciton_cluster.errors import REFUSED_NATIVE_UI_OFF_BACKBURNER, ExcitonValidationError

OPS_PLANNING_SPEC = (
    Path(__file__).resolve().parents[2] / "docs" / "planning" / "operator_product_surface" / "OPS_SPEC.md"
)


def refuse_native_ui_off_backburner(*, allow_native: bool) -> None:
    if allow_native and exciton_backburner_guard() and not exciton_native_ui_allowed():
        raise ExcitonValidationError(
            REFUSED_NATIVE_UI_OFF_BACKBURNER,
            "EXCITON native UI refused while backburner guard is active",
        )


def assert_exciton_backburner_boundary() -> dict[str, object]:
    spec_text = OPS_PLANNING_SPEC.read_text(encoding="utf-8") if OPS_PLANNING_SPEC.is_file() else ""
    planning_backburner = "BACKBURNER" in spec_text
    return {
        "backburner_guard_active": exciton_backburner_guard(),
        "runtime_disabled_by_default": not exciton_enabled(),
        "native_ui_not_allowed_by_default": not exciton_native_ui_allowed(),
        "planning_spec_present": OPS_PLANNING_SPEC.is_file(),
        "planning_spec_declares_backburner": planning_backburner,
        "native_ui_deferred": exciton_backburner_guard() and not exciton_native_ui_allowed(),
    }


__all__ = ["assert_exciton_backburner_boundary", "refuse_native_ui_off_backburner"]
