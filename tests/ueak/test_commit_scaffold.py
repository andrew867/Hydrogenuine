"""UEAK Phase 1 commit scaffold tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.bus import EventBus
from hg_runtime.handlers import StubKernelHandler
from hg_runtime.replay import replay
from hg_ueak.commit_scaffold import CommitScaffold, request_from_decision
from hg_ueak.types import ExecutionRequest


def _decision(**action_overrides):
    action = {
        "action_type": "oea_stub_log",
        "capability_id": "cap.oea_stub_log",
        "effect_class": "audit_log",
        "summary": "internal",
    }
    action.update(action_overrides)
    return {
        "type": "DECISION_EVENT",
        "event_id": "evt_decision",
        "payload": {
            "decision_id": "dec_1",
            "proposal_id": "prop_1",
            "verdict": "allow_stub",
            "action": action,
        },
    }


def test_permitted_internal_effect_commits():
    scaffold = CommitScaffold()
    drafts = scaffold.execute([_decision()], {})

    assert len(drafts) == 1
    assert drafts[0]["type"] == "UEAK_EXECUTION_COMMITTED"
    assert drafts[0]["payload"]["reason_code"] == "committed_internal"
    assert drafts[0]["payload"]["capability_id"] == "cap.oea_stub_log"


def test_unpermitted_external_effect_is_denied_without_permit():
    scaffold = CommitScaffold()
    drafts = scaffold.execute(
        [
            _decision(
                action_type="external_post",
                capability_id="cap.external_post",
                effect_class="external_write",
            )
        ],
        {},
    )

    assert len(drafts) == 1
    assert drafts[0]["type"] == "UEAK_EXECUTION_DENIED"
    assert drafts[0]["payload"]["reason_code"] == "capability_denied"


def test_missing_permit_denies_permit_gated_effect():
    scaffold = CommitScaffold()
    drafts = scaffold.execute(
        [
            _decision(
                action_type="external_write_scaffold",
                capability_id="cap.external_write_scaffold",
                effect_class="external_write",
            )
        ],
        {},
    )

    assert drafts[0]["type"] == "UEAK_EXECUTION_DENIED"
    assert drafts[0]["payload"]["reason_code"] == "missing_permit"


def test_permitted_external_effect_commits_with_permit_ref():
    scaffold = CommitScaffold()
    drafts = scaffold.execute(
        [
            _decision(
                action_type="external_write_scaffold",
                capability_id="cap.external_write_scaffold",
                effect_class="external_write",
                permit_ref="gpp_perm_test123",
            )
        ],
        {},
    )

    assert drafts[0]["type"] == "UEAK_EXECUTION_COMMITTED"


def test_capability_denied_even_with_permit():
    scaffold = CommitScaffold()
    drafts = scaffold.execute(
        [
            _decision(
                action_type="external_post",
                capability_id="cap.external_post",
                effect_class="external_write",
                permit_ref="gpp_perm_test123",
            )
        ],
        {},
    )
    # external_post has bind_allowed=False in registry
    assert drafts[0]["type"] == "UEAK_EXECUTION_DENIED"
    assert drafts[0]["payload"]["reason_code"] == "capability_denied"


def test_request_from_decision_builds_execution_request():
    request = request_from_decision(_decision())

    assert isinstance(request, ExecutionRequest)
    assert request.required_capability == "cap.oea_stub_log"
    assert request.effect_class == "audit_log"


def test_no_external_side_effects_in_ueak_modules():
    forbidden_imports = ("import requests", "import httpx", "import urllib", "import subprocess", "import socket", "hg_oea")
    for path in Path("hg_ueak").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_imports:
            assert token not in text, f"{path} must not reference {token}"


def test_kernel_path_replay_preserves_committed_state(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime")
    kernel = StubKernelHandler()
    drafts = kernel.execute([_decision()], {})
    for draft in drafts:
        bus.emit_draft(draft, source="handler:test")

    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["executions"]["committed"] == 1
    assert result.state["activity"]["executions"]["oea_stub_logged"] == 1
