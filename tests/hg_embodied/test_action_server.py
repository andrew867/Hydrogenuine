from __future__ import annotations

from hg_embodied.ros_bridge.action_server import ActionServer
from hg_embodied.ros_bridge.transport import MockRosTransport


def test_action_server_accepts_and_completes_task():
    transport = MockRosTransport()
    server = ActionServer("ent-1", transport)
    goal = server.send_goal("navigate", {"target": "home"})
    assert goal.status == "succeeded"
    assert goal.goal_id in server.results
    feedback = transport.messages_on("/hg/entity/ent-1/execute_task/feedback")
    assert len(feedback) >= 2
    result_msgs = transport.messages_on("/hg/entity/ent-1/execute_task/result")
    assert result_msgs[-1]["status"] == "succeeded"
