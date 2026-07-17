"""Web queue runtime and adapter tests."""

from __future__ import annotations

import pytest

from hg_runtime.web_action_queue.action_types import WebActionType
from hg_runtime.web_action_queue.adapters import (
    create_web_download_request,
    create_web_form_submit_request,
    create_web_login_request,
    create_web_purchase_request,
    create_web_read_request,
    web_action_to_operator_queue_item,
)
from hg_runtime.web_action_queue.errors import WebQueueCorruptError
from hg_runtime.web_action_queue.policy import classify_web_policy, requires_operator_queue
from hg_runtime.web_action_queue.quarantine import quarantine_root
from hg_runtime.web_action_queue.schema import WebActionDecisionKind, WebActionStatus
from tests.web_action_queue.conftest import make_runtime


def test_enqueue_read_url(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(create_web_read_request("https://example.com"))
    assert item.web_action_id
    assert item.status in (WebActionStatus.QUEUED, WebActionStatus.EXECUTED_READ_ONLY)


def test_download_quarantined(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(
        create_web_download_request("https://example.com/file.pdf", filename="file.pdf")
    )
    assert item.status == WebActionStatus.QUARANTINED
    assert item.quarantine_ref
    meta_dir = quarantine_root(tmp_path) / item.quarantine_ref
    assert (meta_dir / "metadata.json").is_file()


def test_form_submit_denied(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(create_web_form_submit_request("https://example.com/form"))
    assert item.status == WebActionStatus.DENIED


def test_login_purchase_denied(tmp_path):
    q = make_runtime(tmp_path)
    login = q.enqueue(create_web_login_request("https://example.com/login"))
    purchase = q.enqueue(create_web_purchase_request("https://example.com/cart"))
    assert login.status == WebActionStatus.DENIED
    assert purchase.status == WebActionStatus.DENIED


def test_adapter_creates_operator_queue_item():
    req = create_web_read_request("https://example.com")
    item = web_action_to_operator_queue_item(req)
    assert item.queue_item_id
    assert item.action_request.action_type.value == "web_read_url"


def test_side_effect_requires_operator_queue(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(create_web_read_request("https://example.com"))
    pol = classify_web_policy(WebActionType.WEB_READ_URL, live_browser_enabled=False)
    if requires_operator_queue(pol):
        assert item.operator_queue_item_ref


def test_no_direct_execution(tmp_path):
    q = make_runtime(tmp_path)
    assert not hasattr(q, "execute")


def test_no_authority_or_permission(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(create_web_read_request("https://example.com"))
    p = item.to_payload()
    assert p["authority_created"] is False
    assert p["permission_granted"] is False


def test_stable_hash(tmp_path):
    q = make_runtime(tmp_path)
    item = q.enqueue(create_web_read_request("https://example.com"))
    h1 = item.to_payload()["web_action_hash"]
    h2 = item.to_payload()["web_action_hash"]
    assert h1 == h2


def test_receipt_written(tmp_path):
    q = make_runtime(tmp_path)
    q.enqueue(create_web_read_request("https://example.com"))
    receipts = q.store.receipts_path.read_text(encoding="utf-8")
    assert "web-action-receipt" in receipts or "ALLOW_READ_ONLY" in receipts or "QUEUE" in receipts


def test_corrupt_queue_fails_closed(tmp_path):
    q = make_runtime(tmp_path)
    q.enqueue(create_web_read_request("https://example.com"))
    q.store.queue_path.write_text("{bad", encoding="utf-8")
    with pytest.raises(WebQueueCorruptError):
        q.store.load()


def test_stop_panic_blocks_side_effect_eligibility(tmp_path, monkeypatch):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "PANIC").write_text("1", encoding="utf-8")
    import hg_runtime.web_action_queue.queue as wq

    monkeypatch.setattr(wq, "WORKSPACE", tmp_path)
    import hg_runtime.operator_action_queue.stop_panic_policy as spp

    monkeypatch.setattr(spp, "WORKSPACE", tmp_path)
    q = make_runtime(tmp_path)
    pol = classify_web_policy(
        WebActionType.WEB_CLICK_LINK,
        panic_active=True,
    )
    assert pol.decision == WebActionDecisionKind.BLOCKED_BY_PANIC
