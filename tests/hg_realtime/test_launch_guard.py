"""Tests for social-media in-flight launch guard."""

from unittest.mock import MagicMock, patch

from hg_realtime.integrations.launch_guard import should_skip_launch, social_workflow_in_flight


def test_should_skip_launch_non_social_workflow():
    skip, reason = should_skip_launch("overseer-monitor", {})
    assert skip is False
    assert reason == ""


@patch("hg_realtime.integrations.launch_guard.social_workflow_in_flight", return_value=True)
def test_should_skip_launch_when_social_in_flight(mock_in_flight):
    skip, reason = should_skip_launch("social-media", {"task_name": "fourclaw-engage"})
    assert skip is True
    assert "in flight" in reason
    mock_in_flight.assert_called_once()


@patch("hg_gateway.db.get_connection")
def test_social_workflow_in_flight_active_row(mock_conn):
    cursor = MagicMock()
    cursor.execute.return_value.fetchone.return_value = {"run_id": "abc", "status": "running"}
    cm = MagicMock()
    cm.__enter__.return_value = cursor
    mock_conn.return_value = cm
    assert social_workflow_in_flight() is True
