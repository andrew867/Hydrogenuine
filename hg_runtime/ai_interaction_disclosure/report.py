"""AID status report payload — advisory summary for gate/audit."""

from __future__ import annotations

from typing import Mapping


def build_status_report(result: Mapping[str, object]) -> dict[str, object]:
    """Summarize AID service result for proof bundles and audits."""
    return {
        "schema": "aid-status-report",
        "status": result.get("status"),
        "interaction_id": result.get("interaction_id"),
        "permission_granted": False,
        "authority_created": False,
        "aid_enabled": result.get("aid_enabled"),
        "draft_count": result.get("draft_count", 0),
        "emitted_count": result.get("emitted_count", 0),
        "has_disclosure": result.get("disclosure") is not None,
        "has_mode_card": result.get("mode_card") is not None,
        "report_is_not_permission": True,
    }


__all__ = ["build_status_report"]
