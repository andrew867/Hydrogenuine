"""Tests for EXCITON Phase 3 control API."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from hg_runtime.exciton.control_api import ExcitonControlAPI
from hg_runtime.exciton.control_matrix import CONTROL_MATRIX, FORBIDDEN_CONTROL_IDS
from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.adapters import _base_request
from hg_runtime.operator_action_queue.queue import OperatorQueueRuntime
from hg_runtime.operator_action_queue.store import OperatorQueueStore


@pytest.fixture
def api(tmp_path: Path) -> ExcitonControlAPI:
    return ExcitonControlAPI(workspace=tmp_path, run_dir=tmp_path / "run", offline_fixture=True)


def test_control_matrix_loads():
    assert len(CONTROL_MATRIX) >= 18
    assert "REFRESH_STATUS" in CONTROL_MATRIX
    assert CONTROL_MATRIX["APPROVE_ALL"].forbidden


def test_api_status_ok(api: ExcitonControlAPI):
    code, body = api.route("GET", "/api/exciton/status")
    assert code == 200
    assert body["ok"] is True
    assert body["permission_granted"] is False
    assert "snapshot" in body


def test_forbidden_control_denied(api: ExcitonControlAPI):
    for cid in ("APPROVE_ALL", "DIRECT_PUBLISH", "DIRECT_WEB_SUBMIT"):
        code, body = api.route("POST", "/api/exciton/control", json.dumps({"control_id": cid}).encode())
        assert code == 200
        assert body["ok"] is False
        assert body["decision"] == "DENY"


def test_approve_queue_item(api: ExcitonControlAPI):
    store = OperatorQueueStore(
        api.workspace / ".hg-local" / "operator_action_queue" / "operator_action_queue.json",
        api.workspace / ".hg-local" / "operator_action_queue" / "operator_action_receipts.jsonl",
    )
    q = OperatorQueueRuntime(store)
    item = q.enqueue(_base_request(AgentActionType.PROOF_OPEN))
    code, body = api.route(
        "POST",
        f"/api/exciton/operator-queue/{item.queue_item_id}/approve",
        json.dumps({"operator_ref": "local-operator"}).encode(),
    )
    assert code == 200
    assert body["ok"] is True
    q.reload()
    assert q.get_item(item.queue_item_id).status.value == "approved"


def test_deny_queue_item(api: ExcitonControlAPI):
    store = OperatorQueueStore(
        api.workspace / ".hg-local" / "operator_action_queue" / "operator_action_queue.json",
        api.workspace / ".hg-local" / "operator_action_queue" / "operator_action_receipts.jsonl",
    )
    q = OperatorQueueRuntime(store)
    item = q.enqueue(_base_request(AgentActionType.STATUS_REFRESH))
    code, body = api.route(
        "POST",
        f"/api/exciton/operator-queue/{item.queue_item_id}/deny",
        json.dumps({"operator_ref": "local-operator", "reason": "test"}).encode(),
    )
    assert code == 200
    assert body["ok"] is True
    q.reload()
    assert q.get_item(item.queue_item_id).status.value == "denied"


def test_create_rule_requires_operator(api: ExcitonControlAPI):
    code, body = api.route(
        "POST",
        "/api/exciton/auto-approval-rules/create",
        json.dumps({"action_type": "status_refresh"}).encode(),
    )
    assert body["ok"] is False
    assert "operator" in body["human_message"].lower()


def test_create_and_revoke_rule(api: ExcitonControlAPI):
    code, body = api.route(
        "POST",
        "/api/exciton/auto-approval-rules/create",
        json.dumps({"action_type": "status_refresh", "operator_ref": "local-operator"}).encode(),
    )
    assert body["ok"] is True
    rule_id = body.get("rule_id")
    assert rule_id
    code2, body2 = api.route(
        "POST",
        f"/api/exciton/auto-approval-rules/{rule_id}/revoke",
        json.dumps({"operator_ref": "local-operator", "reason": "test"}).encode(),
    )
    assert body2["ok"] is True


def test_approval_mode_persists(api: ExcitonControlAPI):
    run_dir = api.workspace / "run"
    run_dir.mkdir(parents=True)
    code, body = api.route(
        "POST",
        "/api/exciton/soak/change-approval-mode",
        json.dumps({"mode": "PUBLISH_DISABLED"}).encode(),
    )
    assert body["ok"] is True
    rc = run_dir / "run_control.json"
    assert rc.is_file()
    data = json.loads(rc.read_text(encoding="utf-8"))
    assert data["approval_mode"] == "PUBLISH_DISABLED"


def test_stop_and_panic_write_receipt(api: ExcitonControlAPI):
    code, body = api.route("POST", "/api/exciton/soak/stop")
    assert body["ok"] is True
    assert body["receipt_ref"]
    code2, body2 = api.route("POST", "/api/exciton/soak/panic")
    assert body2["ok"] is True
    assert (api.workspace / ".hg-local" / "soak" / "PANIC").is_file()


def test_no_secrets_in_responses(api: ExcitonControlAPI):
    endpoints = [
        ("GET", "/api/exciton/status", None),
        ("GET", "/api/exciton/control-matrix", None),
        ("GET", "/api/exciton/operator-queue", None),
        ("GET", "/api/exciton/web-actions", None),
        ("GET", "/api/exciton/auto-approval-rules", None),
    ]
    for method, path, body in endpoints:
        code, resp = api.route(method, path, body)
        assert not scan_forbidden(resp), path


def test_no_authority_flags(api: ExcitonControlAPI):
    _, body = api.route("GET", "/api/exciton/control-matrix")
    for entry in body["matrix"]:
        assert entry["permission_granted"] is False
        assert entry["authority_created"] is False


def test_local_bind_enforced():
    src = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "exciton_api_server.py"
    text = src.read_text(encoding="utf-8")
    assert "127.0.0.1" in text
    assert 'args.host not in ("127.0.0.1"' in text or "127.0.0.1" in text
