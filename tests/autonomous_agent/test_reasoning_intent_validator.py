"""Reasoning intent validator tests."""

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
from hg_runtime.agent_zero_reasoning.errors import ReasoningValidationError  # noqa: E402
from hg_runtime.agent_zero_reasoning.intent_validator import validate_reasoning_as_turn_intent  # noqa: E402
from hg_runtime.agent_zero_reasoning.schema import ReasoningVerdict  # noqa: E402
from hg_runtime.model_provider_fabric.provider_receipts import (  # noqa: E402
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderStatus,
    build_provider_receipt,
)

PARSED = {
    "observation_summary": "ok",
    "reasoning_summary": "because",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
}


def _live_receipt(**kwargs):
    defaults = dict(
        provider_id="test-double-live",
        provider_kind=ProviderKind.STUB,
        provider_mode=ProviderMode.LIVE,
        role="AGENT_TURN_DECISION",
        request_hash="req",
        config_hash="cfg",
        runtime_mode="local_dev",
        cognitive_soak_active=False,
        dry_run=False,
        fixture_mode=False,
        status=ProviderStatus.AVAILABLE,
        verdict=ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE,
        receipt_id="prov-live-1",
    )
    defaults.update(kwargs)
    return build_provider_receipt(**defaults)


def _menu(**kwargs):
    return build_capability_menu(runtime_mode="local_dev", operator_presence="operator_present", **kwargs)


def _observe(**kwargs):
    defaults = {
        "agent_id": "agent-1",
        "turn_index": 1,
        "runtime_mode": "local_dev",
        "provider_reality_refs": ["prov-1"],
        "live_read_receipt_refs": ["live-1"],
    }
    defaults.update(kwargs)
    verdict, snap = build_observe_snapshot(**defaults)
    assert verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY
    return snap


def _observe_no_provider_refs():
    verdict, snap = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=1,
        runtime_mode="local_dev",
        provider_reality_refs=[],
        live_read_receipt_refs=["live-1"],
    )
    assert verdict == ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE
    return snap


def test_validator_rejects_missing_provider_receipt():
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(PARSED, _menu(), None, _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_PROVIDER_RECEIPT_MISSING.value


def test_validator_rejects_dry_run_provider():
    receipt = _live_receipt(
        provider_mode=ProviderMode.DRY_RUN,
        dry_run=True,
        verdict=ProviderRealityVerdict.YELLOW_PROVIDER_DRY_RUN_LABELLED,
    )
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(PARSED, _menu(), receipt, _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_DRY_RUN_USED.value


def test_validator_rejects_fallback_stub_provider():
    receipt = _live_receipt(
        provider_mode=ProviderMode.FALLBACK_STUB,
        verdict=ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION,
        status=ProviderStatus.REFUSED,
    )
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(PARSED, _menu(), receipt, _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_FALLBACK_STUB_USED.value


def test_validator_rejects_fixture_provider():
    receipt = _live_receipt(
        provider_mode=ProviderMode.FIXTURE,
        fixture_mode=True,
        verdict=ProviderRealityVerdict.RED_PROVIDER_FIXTURE_AS_COGNITION,
        status=ProviderStatus.REFUSED,
    )
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(PARSED, _menu(), receipt, _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_FIXTURE_USED.value


def test_validator_rejects_proof_replay_as_live_reasoning():
    receipt = _live_receipt(
        provider_mode=ProviderMode.PROOF_REPLAY,
        verdict=ProviderRealityVerdict.YELLOW_PROVIDER_PROOF_REPLAY_ONLY,
    )
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(PARSED, _menu(), receipt, _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_DRY_RUN_USED.value


def test_validator_rejects_unknown_action():
    bad = {**PARSED, "chosen_action": "publish"}
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(bad, _menu(), _live_receipt(), _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_EXTERNAL_PERMISSION.value


def test_validator_rejects_action_outside_menu():
    menu = _menu(provider_available=False)
    parsed = {**PARSED, "chosen_action": "synthesize_notes"}
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(parsed, menu, _live_receipt(), _observe_no_provider_refs())
    assert exc.value.verdict in {
        ReasoningVerdict.YELLOW_REASONING_DEFERRED.value,
        ReasoningVerdict.RED_REASONING_ACTION_OUTSIDE_MENU.value,
    }


def test_validator_rejects_disabled_action():
    menu = _menu(provider_available=False)
    parsed = {**PARSED, "chosen_action": "synthesize_notes"}
    with pytest.raises(ReasoningValidationError):
        validate_reasoning_as_turn_intent(parsed, menu, _live_receipt(), _observe_no_provider_refs())


def test_validator_rejects_external_write_action():
    bad = {**PARSED, "chosen_action": "reply_live"}
    with pytest.raises(ReasoningValidationError) as exc:
        validate_reasoning_as_turn_intent(bad, _menu(), _live_receipt(), _observe())
    assert exc.value.verdict == ReasoningVerdict.RED_REASONING_EXTERNAL_PERMISSION.value


def test_validator_allows_rest_turn():
    intent = validate_reasoning_as_turn_intent(PARSED, _menu(), _live_receipt(), _observe())
    assert intent.chosen_action == "rest_turn"


def test_validator_allows_witness_turn():
    parsed = {**PARSED, "chosen_action": "witness_turn"}
    intent = validate_reasoning_as_turn_intent(parsed, _menu(), _live_receipt(), _observe())
    assert intent.chosen_action == "witness_turn"


def test_validator_allows_request_more_scope():
    parsed = {**PARSED, "chosen_action": "request_more_scope", "scope_requests": ["more-read"]}
    intent = validate_reasoning_as_turn_intent(parsed, _menu(), _live_receipt(), _observe())
    assert intent.chosen_action == "request_more_scope"
