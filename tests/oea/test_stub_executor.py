"""OEA Phase 1 stub executor tests."""

from __future__ import annotations

from pathlib import Path

from hg_oea.executor import OEAStubExecutor


def test_oea_refuses_non_committed_refs():
    executor = OEAStubExecutor()
    assert executor.dispatch_committed(
        [
            {
                "type": "DECISION_EVENT",
                "event_id": "evt_decision",
                "payload": {"decision_id": "dec_1"},
            }
        ]
    ) == []
    assert executor.effect_records == []


def test_oea_refuses_legacy_action_committed_shape():
    executor = OEAStubExecutor()
    assert executor.dispatch_committed(
        [
            {
                "type": "ACTION_COMMITTED",
                "event_id": "evt_legacy",
                "payload": {"token_id": "tok_1", "action": {"action_type": "oea_stub_log"}},
            }
        ]
    ) == []


def test_oea_accepts_ueak_execution_committed_only():
    executor = OEAStubExecutor()
    drafts = executor.dispatch_committed(
        [
            {
                "type": "UEAK_EXECUTION_COMMITTED",
                "event_id": "evt_commit",
                "payload": {
                    "commit_ref": "ueak_commit_1",
                    "request_id": "exec_req_1",
                    "effect_class": "audit_log",
                    "action": {"action_type": "oea_stub_log"},
                },
            }
        ]
    )

    assert len(drafts) == 2
    assert drafts[0]["type"] == "OEA_EFFECT_STUB_RECORDED"
    assert drafts[1]["type"] == "EFFECT_RECEIPTED"
    assert drafts[0]["payload"]["commit_ref"] == "ueak_commit_1"
    assert drafts[1]["payload"]["commit_ref"] == "ueak_commit_1"
    assert executor.effect_records[0]["status"] == "stub_logged"


def test_no_external_side_effects_in_oea_modules():
    forbidden = ("requests.", "httpx.", "urllib.", "subprocess.", "socket.")
    for path in Path("hg_oea").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"
