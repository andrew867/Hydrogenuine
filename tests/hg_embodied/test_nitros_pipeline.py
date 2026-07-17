from __future__ import annotations

from hg_embodied.isaac_bridge.nitros_pipeline import default_perception_pipeline, validate_pipeline


def test_default_pipeline_valid():
    cfg = default_perception_pipeline("robot-1")
    assert validate_pipeline(cfg) == []
    assert "/robot-1/camera/rgb" in cfg.input_topics
