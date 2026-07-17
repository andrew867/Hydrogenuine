"""Reasoning provider adapter tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.capability_menu import build_capability_menu  # noqa: E402
from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot  # noqa: E402
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict  # noqa: E402
from hg_runtime.agent_zero_reasoning.errors import ReasoningProviderError  # noqa: E402
from hg_runtime.agent_zero_reasoning.provider_adapter import request_turn_decision_from_provider  # noqa: E402
from hg_runtime.agent_zero_reasoning.schema import (  # noqa: E402
    ReasoningContext,
    ReasoningRequest,
    ReasoningVerdict,
    build_reasoning_request,
)
from hg_runtime.model_provider_fabric.provider_receipts import (  # noqa: E402
    ProviderFallbackDenied,
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderStatus,
    ProviderUnavailable,
    build_provider_receipt,
)

VALID_OUTPUT = json.dumps({
    "observation_summary": "ok",
    "reasoning_summary": "rest",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
})


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_INFER_DRY_RUN", "0")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)


def _context():
    verdict, snap = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=1,
        runtime_mode="local_dev",
        provider_reality_refs=["prov-1"],
        live_read_receipt_refs=["live-1"],
    )
    assert verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY
    menu = build_capability_menu(runtime_mode="local_dev")
    return ReasoningContext(
        charter_text_hash="charter-hash",
        observe_snapshot=snap,
        capability_menu=menu,
        agent_state_summary={"agent_id": "agent-1", "turn_index": 0},
    )


def _request():
    return build_reasoning_request(
        agent_id="agent-1",
        turn_index=1,
        agent_state_ref="state-1",
        observe_snapshot_ref="snap-1",
        capability_menu_ref="menu-1",
        prompt_hash="prompt-hash",
        runtime_mode="local_dev",
    )


def test_provider_unavailable_returns_yellow_failure_not_fake_intent():
    with pytest.raises(ProviderUnavailable) as exc:
        request_turn_decision_from_provider(_request(), _context())
    assert exc.value.receipt.verdict == ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE


def test_empty_provider_output_returns_red(monkeypatch):
    def _empty_invoke(_prompt, _receipt):
        return "   "

    with pytest.raises(ReasoningProviderError) as exc:
        request_turn_decision_from_provider(_request(), _context(), provider_invoke=_empty_invoke)
    assert exc.value.receipt is not None
    assert exc.value.receipt.verdict == ProviderRealityVerdict.RED_PROVIDER_EMPTY_OUTPUT


def test_valid_test_double_live_provider_output():

    def _test_double_invoke(_prompt, _receipt):
        return VALID_OUTPUT

    receipt, raw = request_turn_decision_from_provider(
        _request(),
        _context(),
        provider_invoke=_test_double_invoke,
    )
    assert receipt.receipt_id
    assert receipt.provider_mode == ProviderMode.LIVE
    assert "rest_turn" in raw


def test_fallback_stub_raises_not_green(monkeypatch):
    monkeypatch.setenv("HG_PROVIDER_FALLBACK_ALLOWED", "true")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    with pytest.raises((ProviderFallbackDenied, ProviderUnavailable)):
        request_turn_decision_from_provider(_request(), _context())
