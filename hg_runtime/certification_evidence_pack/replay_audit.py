"""CRT passive replay audit over RTC logs."""

from __future__ import annotations

from pathlib import Path

from hg_core.boundary_full.replay_audit import classify_event_log


def audit_crt_events(paths: list[Path]) -> dict[str, object]:
    def _handler(payload: dict[str, object]) -> dict[str, object] | None:
        snapshot_id = payload.get("snapshot_id")
        claim_id = payload.get("claim_id")
        export_id = payload.get("export_id")
        key = snapshot_id or claim_id or export_id
        if not key:
            return None
        return {
            "key": key,
            "observation_only": True,
            "permission_granted": False,
            "certification_granted": False,
        }

    return classify_event_log(paths, type_prefix="CRT_", handler=_handler)


__all__ = ["audit_crt_events"]
