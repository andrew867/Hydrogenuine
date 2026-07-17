"""Stop/panic and policy tests."""

from __future__ import annotations

import pytest

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.operator_action_queue.errors import StopPanicActiveError
from hg_runtime.operator_action_queue.policy import (
    high_risk_not_executable_in_phase3,
    item_execution_eligible,
)
from hg_runtime.operator_action_queue.stop_panic_policy import StopPanicState
from tests.operator_action_queue.conftest import make_runtime, sample_request


def test_panic_blocks_approval(tmp_path, monkeypatch):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "PANIC").write_text("1", encoding="utf-8")

    import hg_runtime.operator_action_queue.stop_panic_policy as spp

    monkeypatch.setattr(spp, "WORKSPACE", tmp_path)
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.OPERATOR_NOTE))
    with pytest.raises(StopPanicActiveError):
        q.approve_item(item.queue_item_id, "local-operator")


def test_stop_blocks_approval(tmp_path, monkeypatch):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "STOP").write_text("1", encoding="utf-8")

    import hg_runtime.operator_action_queue.stop_panic_policy as spp

    monkeypatch.setattr(spp, "WORKSPACE", tmp_path)
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.OPERATOR_NOTE))
    with pytest.raises(StopPanicActiveError):
        q.approve_item(item.queue_item_id, "local-operator")


def test_queue_readable_during_stop_panic(tmp_path, monkeypatch):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "PANIC").write_text("1", encoding="utf-8")

    import hg_runtime.operator_action_queue.stop_panic_policy as spp

    monkeypatch.setattr(spp, "WORKSPACE", tmp_path)
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    listed = q.list_items()
    assert len(listed) == 1
    assert listed[0].queue_item_id == item.queue_item_id


def test_social_post_requires_approval(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.SOCIAL_POST))
    assert item.status.value == "queued"
    eligible, _ = item_execution_eligible(item, stop_panic=False)
    assert not eligible


def test_web_form_submit_not_executable(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.WEB_FORM_SUBMIT))
    with pytest.raises(Exception):
        q.approve_item(item.queue_item_id, "local-operator")


def test_shell_command_high_risk_not_executable(tmp_path):
    assert high_risk_not_executable_in_phase3(AgentActionType.SHELL_COMMAND)
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.SHELL_COMMAND))
    with pytest.raises(Exception):
        q.approve_item(item.queue_item_id, "local-operator")


def test_stop_panic_state_blocks_execution():
    sp = StopPanicState(panic_active=True)
    assert sp.blocks_execution()
    assert sp.blocks_approval()
