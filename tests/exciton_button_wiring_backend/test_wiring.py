"""Button wiring backend tests — every control has handler or disabled reason."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.exciton.action_handlers import handle_control
from hg_runtime.exciton.control_matrix import CONTROL_MATRIX, FORBIDDEN_CONTROL_IDS, get_matrix


REQUIRED_CONTROLS = [
    "REFRESH_STATUS",
    "OPEN_PROOF",
    "COPY_SAFE_SUMMARY",
    "ADD_OPERATOR_NOTE",
    "APPROVE_ACTION_ITEM",
    "DENY_ACTION_ITEM",
    "EXPIRE_ACTION_ITEM",
    "PAUSE_PUBLISH",
    "RESUME_APPROVED_ONLY",
    "CHANGE_APPROVAL_MODE",
    "CREATE_AUTO_APPROVAL_RULE",
    "REVOKE_AUTO_APPROVAL_RULE",
    "ENQUEUE_WEB_READ",
    "ENQUEUE_WEB_CLICK",
    "ENQUEUE_WEB_DOWNLOAD",
    "STOP_SOAK",
    "PANIC_STOP",
    "FINALIZE_SOAK",
    "TOGGLE_POLLING_LOCAL_UI_ONLY",
]


def test_each_required_control_has_entry():
    for cid in REQUIRED_CONTROLS:
        assert cid in CONTROL_MATRIX
        entry = CONTROL_MATRIX[cid]
        assert entry.forbidden is False
        assert entry.handler or entry.disabled_reason is None


def test_forbidden_controls_denied():
    for cid in FORBIDDEN_CONTROL_IDS:
        if cid not in CONTROL_MATRIX:
            continue
        resp = handle_control(cid, {})
        assert resp["ok"] is False
        assert resp["decision"] == "DENY"


def test_matrix_payload_complete():
    matrix = get_matrix()
    ids = {m["control_id"] for m in matrix}
    for cid in REQUIRED_CONTROLS:
        assert cid in ids


def test_no_fake_success_on_forbidden():
    for cid in ("APPROVE_ALL", "DIRECT_PUBLISH", "DIRECT_LOGIN"):
        resp = handle_control(cid, {})
        assert resp["ok"] is False
        assert resp["receipt_ref"]


def test_stop_panic_not_disabled(tmp_path: Path):
    for cid in ("STOP_SOAK", "PANIC_STOP"):
        entry = CONTROL_MATRIX[cid]
        assert not entry.forbidden
        resp = handle_control(cid, {"workspace": str(tmp_path)})
        assert resp["ok"] is True
        assert resp["decision"] == "FULL_STOP"
