"""Preemption matrix policy (CT-06 ADM)."""

from __future__ import annotations

from hg_core.admission.types import MutatingKind

# Row = holder, column = arriving request → arriving fate
_MATRIX: dict[tuple[MutatingKind, MutatingKind], str] = {
    ("panic", "crr_recovery"): "wait",
    ("panic", "srp_apply"): "refuse",
    ("panic", "mel_cycle"): "refuse",
    ("panic", "oea_effect"): "refuse",
    ("panic", "ter_command"): "refuse",
    ("crr_recovery", "srp_apply"): "refuse",
    ("crr_recovery", "mel_cycle"): "preempt",
    ("crr_recovery", "oea_effect"): "queue",
    ("crr_recovery", "ter_command"): "queue",
    ("srp_apply", "srp_apply"): "refuse",
    ("srp_apply", "mel_cycle"): "queue",
    ("mel_cycle", "mel_cycle"): "refuse",
}


def arriving_fate(*, holder: MutatingKind | None, arriving: MutatingKind, panic_active: bool) -> str:
    if panic_active and arriving != "panic":
        return "refuse"
    if holder is None:
        return "admit"
    return _MATRIX.get((holder, arriving), "admit")


__all__ = ["arriving_fate"]
