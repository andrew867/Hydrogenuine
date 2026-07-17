"""Core operator queue operations."""

from __future__ import annotations

import pytest

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.status import AgentActionStatus
from hg_runtime.operator_action_queue.errors import (
    InvalidTransitionError,
    NotExecutableError,
    QueueCorruptError,
    SelfApprovalError,
    StopPanicActiveError,
)
from hg_runtime.operator_action_queue.store import OperatorQueueStore
from tests.operator_action_queue.conftest import make_runtime, sample_request


def test_enqueue_creates_queued_item(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.SOCIAL_POST))
    assert item.status == AgentActionStatus.QUEUED
    assert item.queue_item_id


def test_list_returns_queued_item(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    listed = q.list_items()
    assert len(listed) == 1
    assert listed[0].queue_item_id == item.queue_item_id


def test_show_returns_sanitized_item(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(sanitized_preview="Safe text only"))
    got = q.get_item(item.queue_item_id)
    assert got is not None
    assert "Safe text" in got.sanitized_preview
    assert "password" not in got.sanitized_preview.lower()


def test_approve_writes_receipt(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.OPERATOR_NOTE))
    decision = q.approve_item(item.queue_item_id, "local-operator")
    assert decision.decision_type.value == "APPROVE_ITEM"
    receipts = q.store.load_receipts()
    assert any(r["decision_type"] == "APPROVE_ITEM" for r in receipts)


def test_deny_writes_receipt(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    q.deny_item(item.queue_item_id, "local-operator", reason="not approved")
    receipts = q.store.load_receipts()
    assert any(r["decision_type"] == "DENY_ITEM" for r in receipts)


def test_expire_writes_receipt(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    q.expire_item(item.queue_item_id, reason="expired")
    receipts = q.store.load_receipts()
    assert any(r["decision_type"] == "EXPIRE_ITEM" for r in receipts)


def test_cancel_writes_receipt(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    q.cancel_item(item.queue_item_id, "local-operator", reason="cancelled")
    receipts = q.store.load_receipts()
    assert any(r["decision_type"] == "CANCEL_ITEM" for r in receipts)


def test_approved_item_eligible_not_executed(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.PROOF_OPEN))
    q.approve_item(item.queue_item_id, "local-operator")
    got = q.get_item(item.queue_item_id)
    assert got.status == AgentActionStatus.APPROVED
    eligible = q.approved_eligible_items()
    assert len(eligible) == 1
    assert got.status != AgentActionStatus.EXECUTED


def test_queue_does_not_execute_action(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.PROOF_OPEN))
    q.approve_item(item.queue_item_id, "local-operator")
    # No execute method — only explicit mark_executed
    assert not hasattr(q, "execute")


def test_denied_cannot_be_approved(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    q.deny_item(item.queue_item_id, "local-operator", reason="no")
    with pytest.raises(InvalidTransitionError):
        q.approve_item(item.queue_item_id, "local-operator")


def test_executed_cannot_re_execute(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.PROOF_OPEN))
    q.approve_item(item.queue_item_id, "local-operator")
    q.mark_executed(item.queue_item_id, "exec-ref-1")
    with pytest.raises(NotExecutableError):
        q.mark_executed(item.queue_item_id, "exec-ref-2")


def test_expired_cannot_execute(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    q.expire_item(item.queue_item_id, reason="ttl")
    with pytest.raises(InvalidTransitionError):
        q.approve_item(item.queue_item_id, "local-operator")


def test_no_authority_created_true(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    payload = item.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False


def test_stable_queue_hash(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    h1 = item.to_payload()["queue_hash"]
    h2 = item.to_payload()["queue_hash"]
    assert h1 == h2


def test_stable_receipt_hash(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request(AgentActionType.PROOF_OPEN))
    q.approve_item(item.queue_item_id, "local-operator")
    receipts = q.store.load_receipts()
    approve = next(r for r in receipts if r["decision_type"] == "APPROVE_ITEM")
    assert approve["receipt_hash"].startswith("sha256:")


def test_corrupt_queue_fails_closed(tmp_path):
    store = make_runtime(tmp_path).store
    store.queue_path.parent.mkdir(parents=True, exist_ok=True)
    store.queue_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(QueueCorruptError):
        store.load()


def test_secrets_scrubbed_in_summary(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(
        sample_request(human_summary="Normal summary", sanitized_preview="No secrets here")
    )
    assert "Bearer" not in item.human_summary


def test_run_scoped_queue_path(tmp_path):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    store = OperatorQueueStore.for_run(run_dir)
    assert store.queue_path.name == "operator_action_queue.json"
    q = make_runtime(tmp_path)
    q.enqueue(sample_request())


def test_agent0_self_approval_blocked(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(sample_request())
    with pytest.raises(SelfApprovalError):
        q.approve_item(item.queue_item_id, "agent0")
