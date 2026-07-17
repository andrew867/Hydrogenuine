"""PRO body-state bridge for embodiment growth — advisory link only."""

from __future__ import annotations

from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.embodiment_oea_growth.types import FIXTURE_CLOCK
from hg_runtime.proprioceptive_body_model import body_state_from_fixture, evaluate_body_state


def link_pro_body_state(
    pro_fixture: dict[str, str],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Evaluate linked PRO body state — reach is not actuation permission."""
    body_state = body_state_from_fixture(pro_fixture)
    evaluation = evaluate_body_state(body_state, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": evaluation.get("status", "recorded"),
        "body_state_id": body_state.body_state_id,
        "pro_evaluation": evaluation,
        "link_only": True,
        "permission_granted": False,
        "reach_is_not_actuation_permission": True,
        "contact_is_not_consent": True,
    }


__all__ = ["link_pro_body_state"]
