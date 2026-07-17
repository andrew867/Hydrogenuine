"""Dispatch bridge tests."""
from __future__ import annotations

from hg_runtime.governed_work_loop.dispatch_bridge import attempt_live_dispatch
from hg_runtime.governed_work_loop.work_envelope import ExternalActionEnvelope


def test_live_dispatch_refused_without_envelope():
    disp = attempt_live_dispatch(None)
    assert disp.external_side_effect is False
    assert disp.refusal_reasons


def test_live_dispatch_refused_without_permit():
    ext = ExternalActionEnvelope(
        external_envelope_id="ext1",
        platform="moltbook",
        allowed_action_types=("publish_post",),
        max_candidates=1,
        max_dry_dispatches=1,
        max_live_dispatches=1,
        requires_phase18_live_permit=True,
        requires_platform_proof=True,
        requires_operator_prearm=True,
        status="armed",
        created_at="t",
        expires_at="t2",
    )
    disp = attempt_live_dispatch(ext, operator_prearm=True)
    assert disp.external_side_effect is False
    assert "RED_LIVE" in disp.refusal_reasons[0] or "YELLOW" in disp.verdict
