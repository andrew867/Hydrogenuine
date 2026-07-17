"""Capability menu snapshot tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.capability_menu import build_capability_menu, validate_capability_menu  # noqa: E402
from hg_runtime.agent_zero_state.types import FORBIDDEN_ACTION_IDS  # noqa: E402


def test_capability_menu_disables_external_write_actions():
    menu = build_capability_menu(runtime_mode="local_dev")
    assert validate_capability_menu(menu)
    for forbidden in FORBIDDEN_ACTION_IDS:
        action = next((a for a in menu.actions if a.action_id == forbidden), None)
        assert action is None or not action.enabled


def test_capability_menu_respects_operator_absence():
    menu = build_capability_menu(
        runtime_mode="local_dev",
        operator_presence="operator_absent",
    )
    observe = next(a for a in menu.actions if a.action_id == "observe_social")
    assert observe.enabled is False
    rest = next(a for a in menu.actions if a.action_id == "rest_turn")
    assert rest.enabled is True


def test_capability_menu_marks_provider_unavailable():
    menu = build_capability_menu(
        runtime_mode="local_dev",
        provider_available=False,
    )
    synth = next(a for a in menu.actions if a.action_id == "synthesize_notes")
    assert synth.enabled is False
    assert synth.disabled_reason == "provider_unavailable"
