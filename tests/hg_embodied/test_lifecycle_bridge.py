from __future__ import annotations

import pytest

from hg_embodied.ros_bridge.lifecycle_bridge import (
    HgEntityState,
    RosLifecycleState,
    can_transition,
    hg_to_ros_state,
    ros_to_hg_state,
)


def test_ros_active_maps_to_hg_active():
    assert ros_to_hg_state(RosLifecycleState.ACTIVE) == HgEntityState.ACTIVE


def test_hg_halted_maps_to_ros_inactive():
    assert hg_to_ros_state(HgEntityState.HALTED) == RosLifecycleState.INACTIVE


def test_invalid_transition_blocked():
    assert can_transition(RosLifecycleState.UNCONFIGURED, RosLifecycleState.ACTIVE) is False
    assert can_transition(RosLifecycleState.INACTIVE, RosLifecycleState.ACTIVE) is True
