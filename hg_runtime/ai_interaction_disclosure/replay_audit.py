"""AID passive replay audit over RTC logs."""

from __future__ import annotations

from pathlib import Path

from hg_core.boundary_full.replay_audit import classify_event_log


def audit_aid_events(paths: list[Path]) -> dict[str, object]:
    def _handler(payload: dict[str, object]) -> dict[str, object] | None:
        interaction_id = payload.get("interaction_id") or payload.get("disclosure_id")
        if not interaction_id:
            return None
        return {
            "interaction_id": interaction_id,
            "observation_only": True,
            "permission_granted": False,
        }

    return classify_event_log(paths, type_prefix="AID_", handler=_handler)


__all__ = ["audit_aid_events"]
