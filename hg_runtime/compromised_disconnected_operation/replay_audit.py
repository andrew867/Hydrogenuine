"""CDO passive replay audit over RTC logs."""

from __future__ import annotations

from pathlib import Path

from hg_core.boundary_full.replay_audit import classify_event_log


def audit_cdo_events(paths: list[Path]) -> dict[str, object]:
    def _handler(payload: dict[str, object]) -> dict[str, object] | None:
        signal_id = payload.get("signal_id")
        if not signal_id:
            return None
        return {
            "signal_id": signal_id,
            "observation_only": True,
            "permission_granted": False,
        }

    return classify_event_log(paths, type_prefix="CDO_", handler=_handler)


__all__ = ["audit_cdo_events"]
