from __future__ import annotations

from hg_embodied.ros_bridge.lifecycle_bridge import HgEntityState, RosLifecycleState
from hg_embodied.ros_bridge.node_adapter import HGEntityNode
from hg_embodied.ros_bridge.transport import MockRosTransport


def test_entity_node_publishes_presence():
    transport = MockRosTransport()
    node = HGEntityNode("ent-1", "per-1", "fp_abc", transport=transport)
    node.configure()
    node.activate()
    topic = node.topic_mapper.ros_topic_for_channel("presence")
    msgs = transport.messages_on(topic)
    assert len(msgs) >= 1
    assert node.ros_state == RosLifecycleState.ACTIVE
    assert node.hg_state == HgEntityState.ACTIVE


def test_entity_node_lifecycle_matches_hg_lifecycle():
    node = HGEntityNode("ent-1", "per-1", "fp_abc", transport=MockRosTransport())
    node.configure()
    assert node.hg_state == HgEntityState.SLEEPING
    node.activate()
    assert node.hg_state == HgEntityState.ACTIVE


def test_entity_node_handles_mesh_coordination():
    transport = MockRosTransport()
    nodes = [
        HGEntityNode("ent-a", "per-a", "fp_shared", transport=transport),
        HGEntityNode("ent-b", "per-b", "fp_shared", transport=transport),
    ]
    received = []
    for n in nodes:
        n.configure()
        n.activate()
        n.subscribe_coordination(lambda m: received.append(m))
    coord_topic = nodes[0].topic_mapper.ros_topic_for_channel("coordination")
    transport.publish(coord_topic, nodes[0].topic_mapper.mesh_to_ros_payload({"type": "job_claim", "job_id": "j1"}))
    assert len(received) >= 2


def test_entity_node_publishes_cognitive_diagnostics():
    transport = MockRosTransport()
    node = HGEntityNode("ent-1", "per-1", "fp_abc", transport=transport)
    node.configure()
    node.activate()
    node.bridge_cognitive_state(emotional=0.7, drift=0.1)
    diag = transport.messages_on("/hg/entity/ent-1/diagnostics")
    assert diag[-1]["emotional"] == 0.7
