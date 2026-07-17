"""SYN passive replay audit over RTC logs."""

from __future__ import annotations

from pathlib import Path

from hg_core.boundary_full.replay_audit import classify_event_log


def audit_syn_events(paths: list[Path]) -> dict[str, object]:
    def _handler(payload: dict[str, object]) -> dict[str, object] | None:
        artifact_id = payload.get("artifact_id")
        if not artifact_id:
            return None
        return {
            "artifact_id": artifact_id,
            "observation_only": True,
            "permission_granted": False,
        }

    return classify_event_log(paths, type_prefix="SYN_", handler=_handler)


__all__ = ["audit_syn_events"]
