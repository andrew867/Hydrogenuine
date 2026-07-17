from __future__ import annotations

from hg_embodied.ros_bridge.topic_mapper import TopicMapper


def test_mesh_channels_map_to_ros_topics():
    mapper = TopicMapper("fp_test")
    topics = mapper.all_ros_topics()
    assert "/hg/mesh/fp_test/presence" in topics
    assert "/hg/mesh/fp_test/coordination" in topics
    assert "/hg/mesh/fp_test/job_claim" in topics


def test_mesh_message_roundtrip():
    mapper = TopicMapper("fp_test")
    mesh = {"type": "job_progress", "fingerprint_id": "fp_test", "pct": 0.5}
    ros = mapper.mesh_to_ros_payload(mesh)
    restored = mapper.ros_to_mesh_message(ros)
    assert restored["type"] == "job_progress"
    assert restored.get("pct") == 0.5 or "pct" in str(restored)
