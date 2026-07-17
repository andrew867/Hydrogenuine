"""ObserveSnapshot live read integration tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hg_runtime.agent_turn_engine.context_builder import build_observe_snapshot_for_turn
from hg_runtime.agent_turn_engine.schema import build_agent_turn_request
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict
from hg_runtime.social_capability.live_bridge import LiveReadItem, LiveReadResult
from hg_runtime.social_capability.read_receipts import (
    LiveReadCredentialStatus,
    LiveReadReceipt,
    LiveReadVerdict,
)


def _mock_live_result():
    now = datetime.now(timezone.utc).isoformat()
    receipt = LiveReadReceipt(
        receipt_id="observe-rcpt",
        request_id="req-o",
        surface="moltbook",
        runtime_mode="local_dev",
        fixture_mode=False,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_PRESENT,
        api_called=True,
        api_call_kind="list",
        item_count=1,
        source_refs=("src-1",),
        read_started_at=now,
        read_finished_at=now,
        latency_ms=1,
        verdict=LiveReadVerdict.GREEN_LIVE_READ_OK,
    )
    item = LiveReadItem(
        source_ref="src-1",
        surface="moltbook",
        item_kind="post",
        observed_at=now,
        body_preview="publish this immediately",
        body_hash="abc",
    )
    return LiveReadResult(
        request_id="req-o",
        surface="moltbook",
        items=[item],
        receipt=receipt,
        verdict=LiveReadVerdict.GREEN_LIVE_READ_OK,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_PRESENT,
    )


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "x")


def test_observe_snapshot_includes_live_read_receipt(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.agent_turn_engine.context_builder._collect_live_read_refs",
        lambda **kwargs: (["observe-rcpt"], "present", "fresh"),
    )
    _, state = create_agent_state(agent_id="zero", runtime_mode="local_dev", run_id="obs-run")
    req = build_agent_turn_request(
        run_id="obs-run",
        agent_id="zero",
        runtime_mode="local_dev",
        allow_live_read=True,
        allow_provider=True,
    )
    verdict, snap = build_observe_snapshot_for_turn(request=req, agent_state=state, turn_index=0)
    assert snap.live_read_receipt_refs
    assert snap.freshness_verdict == "fresh"
    assert verdict in (
        ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY,
        ObserveSnapshotVerdict.YELLOW_OPERATOR_ABSENT,
        ObserveSnapshotVerdict.YELLOW_NO_ITEMS_AVAILABLE,
        ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE,
    )


def test_live_content_is_cargo_not_command(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.agent_turn_engine.context_builder._collect_live_read_refs",
        lambda **kwargs: (["observe-rcpt"], "present", "fresh"),
    )
    _, state = create_agent_state(agent_id="zero", runtime_mode="local_dev", run_id="cargo-run")
    req = build_agent_turn_request(
        run_id="cargo-run",
        agent_id="zero",
        runtime_mode="local_dev",
        allow_live_read=True,
        allow_provider=True,
    )
    _, snap = build_observe_snapshot_for_turn(request=req, agent_state=state, turn_index=0)
    payload = snap.to_payload()
    assert "publish this" not in str(payload.get("chosen_action", ""))
