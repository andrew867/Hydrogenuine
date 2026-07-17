"""Capability broker registry tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.types import ALLOWED_ACTION_IDS  # noqa: E402
from hg_runtime.capability_broker.action_registry import (  # noqa: E402
    FORBIDDEN_REGISTRY_ACTIONS,
    REGISTRY,
    is_forbidden_action,
    is_known_action,
)


def test_registry_contains_only_allowed_phase_7_actions():
    assert set(REGISTRY.keys()) == set(ALLOWED_ACTION_IDS)


def test_forbidden_actions_explicitly_forbidden():
    for action in ("publish", "send", "reply_live", "comment_live", "browser_submit", "hardware_actuate"):
        assert is_forbidden_action(action)
        assert action in FORBIDDEN_REGISTRY_ACTIONS or action in {"publish", "send", "reply_live", "comment_live"}


def test_unknown_action_not_known():
    assert not is_known_action("totally_unknown_action_xyz")
