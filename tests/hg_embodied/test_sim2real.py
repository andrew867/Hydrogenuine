from __future__ import annotations

import pytest

from hg_embodied.isaac_bridge.sim2real import (
    apply_calibration,
    build_sim2real_report,
    record_calibration,
)


def test_sim2real_confidence_high_when_aligned():
    traj = [{"t": 0, "pose": {"x": 0, "y": 0}}, {"t": 1, "pose": {"x": 1, "y": 0}}]
    report = build_sim2real_report("warehouse", traj, traj)
    assert report.confidence_score >= 0.99
    assert report.calibration_recommended is False


def test_calibration_adjusts_pose():
    record_calibration("lab", {"x": 0.1, "y": 0.0, "z": 0.0})
    out = apply_calibration("lab", {"x": 1.0, "y": 2.0, "z": 0.0})
    assert out["x"] == pytest.approx(1.1)
