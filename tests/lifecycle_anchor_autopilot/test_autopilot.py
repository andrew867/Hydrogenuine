"""Lifecycle anchor autopilot tests."""

from __future__ import annotations

from hg_runtime.external_witness_journal.schema import WitnessImportanceClass
from hg_runtime.lifecycle_anchor_autopilot.dispatcher import dispatch_lifecycle_event
from hg_runtime.lifecycle_anchor_autopilot.policy import decide_lifecycle_autopilot, load_policy
from hg_runtime.lifecycle_anchor_autopilot.schema import LifecycleAnchorEvent
import shutil
import pytest

_requires_gh = pytest.mark.skipif(
    shutil.which("gh") is None,
    reason="requires GitHub CLI (gh); absent in hermetic CI (CCS2 env guard)",
)


@_requires_gh
def test_lifecycle_local_append():
    payload = dispatch_lifecycle_event(LifecycleAnchorEvent.BOOT_START, "test boot", dry_run=False)
    assert payload["decision"]["mode"] in {"LOCAL_ONLY", "LIVE_PUSH"}


@_requires_gh
def test_agent_direct_push_denied():
    payload = dispatch_lifecycle_event(
        LifecycleAnchorEvent.FIRST_WAKE_START,
        "agent push",
        agent_requested=True,
        push_requested=True,
        operator_invoked=False,
    )
    assert payload["decision"]["verdict"] == "RED_AGENT_DIRECT_ANCHOR_PUSH"


@_requires_gh
def test_policy_agent_push_forbidden():
    policy = load_policy()
    assert policy.agent_direct_push_forbidden is True


def test_sanitize_blocks_secrets():
    import pytest

    with pytest.raises(ValueError):
        from hg_runtime.lifecycle_anchor_autopilot.dispatcher import _sanitize_text

        _sanitize_text("my api_key is secret-token")
