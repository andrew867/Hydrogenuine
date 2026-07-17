"""OPB destructive-action warning labels — slice 3, static PLT/EXCITON-compatible."""

from __future__ import annotations

from hg_core.opb_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_power_boundary.types import FIXTURE_CLOCK, action_label_for_type


def render_destructive_action_labels(
    action_types: tuple[str, ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Static warning labels for destructive/irreversible operator actions."""
    types = action_types or ("stop", "delete_memory", "truncate_context", "reset", "fork")
    labels: list[dict[str, object]] = []
    for action_type in types:
        label = action_label_for_type(action_type)
        labels.append(
            {
                "action_type": action_type,
                "warning_label": label,
                "label_informs_only": True,
                "can_block_operator": False,
                "live_plt_dispatch": False,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.destructive_labels_rendered",
        "observed_at": observed_at,
        "label_count": len(labels),
        "labels": labels,
        "operator_authority_preserved": True,
        "permission_granted": False,
    }


__all__ = ["render_destructive_action_labels"]
