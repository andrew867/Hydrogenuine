from __future__ import annotations

import time

from hg_embodied.sensor_fusion.attention_allocator import AttentionAllocator
from hg_embodied.sensor_fusion.environmental_model import EnvironmentalModelBuilder
from hg_embodied.sensor_fusion.multimodal_fuser import MultimodalFuser
from hg_embodied.sensor_fusion.thz_adapter import ConsentZone, ThzAdapter
from hg_embodied.sensor_fusion.contracts import SensorFrame


def test_thz_classifies_material():
    adapter = ThzAdapter(robot_id="robot-1")
    result = adapter.classify_material([0.9, 0.2, 0.1, 0.1])
    assert result["material"] == "polymer"
    assert result["confidence"] > 0.5


def test_multimodal_fuser_keeps_latest_per_modality():
    fuser = MultimodalFuser(robot_id="robot-1")
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    fuser.ingest(SensorFrame("f1", "robot-1", "lidar", ts, "ref1"))
    fuser.ingest(SensorFrame("f2", "robot-1", "lidar", ts, "ref2"))
    fused = fuser.fuse()
    assert fused["modalities"]["lidar"]["data_ref"] == "ref2"


def test_environmental_model_human_detection():
    builder = EnvironmentalModelBuilder(robot_id="robot-1")
    fused = {
        "modalities": {
            "camera": {
                "metadata": {"human_detected": True, "human_distance_m": 0.8},
            }
        }
    }
    model = builder.update_from_fusion(fused)
    assert builder.human_within_threshold(model) is True


def test_attention_allocator_splits_budget():
    alloc = AttentionAllocator(total_budget_hz=30.0)
    rates = alloc.allocate(["lidar", "camera", "thz"])
    assert abs(sum(rates.values()) - 30.0) < 0.01
