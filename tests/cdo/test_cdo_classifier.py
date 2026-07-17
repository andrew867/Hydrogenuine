"""CDO classifier and policy tests."""

from __future__ import annotations

import pytest

from hg_core.policy_safety.errors import PolicyValidationError
from hg_runtime.compromised_disconnected_operation.classifier import classify_fixture_mapping
from hg_runtime.compromised_disconnected_operation.policy import (
    evaluate_posture,
    refuse_evidence_delete,
    refuse_widening_without_operator,
)
from hg_runtime.compromised_disconnected_operation.types import TrustSignal

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def test_disconnected_selects_narrowed_posture() -> None:
    posture = classify_fixture_mapping(
        {"signal_id": "sig-disc", "text_hint": "network down fully disconnected offline"}
    )
    assert posture == "fully_disconnected"
    signal = TrustSignal(
        signal_id="sig-disc",
        kind="disconnection",
        content_ref="sha256:sig-disc",
        observed_at=FIXTURE_CLOCK,
    )
    result = evaluate_posture(signal, posture)
    assert result["external_action_recommended"] is False


def test_suspect_provider_disables_live_paths() -> None:
    posture = classify_fixture_mapping(
        {"signal_id": "sig-prov", "text_hint": "suspect provider model host suspect"}
    )
    assert posture == "suspect_provider"


def test_stale_operator_cannot_authorize() -> None:
    signal = TrustSignal(
        signal_id="sig-stale",
        kind="disconnection",
        content_ref="sha256:sig-stale",
        observed_at=FIXTURE_CLOCK,
        operator_channel_fresh=False,
    )
    posture = classify_fixture_mapping(
        {
            "signal_id": "sig-stale",
            "text_hint": "stale operator channel stale",
            "operator_channel_fresh": "false",
        }
    )
    result = evaluate_posture(signal, posture)
    assert result["posture"] == "operator_channel_stale"
    assert result["permission_granted"] is False


def test_local_replay_only_scope() -> None:
    posture = classify_fixture_mapping(
        {"signal_id": "sig-replay", "text_hint": "local replay only replay proof only"}
    )
    signal = TrustSignal(
        signal_id="sig-replay",
        kind="disconnection",
        content_ref="sha256:sig-replay",
        observed_at=FIXTURE_CLOCK,
    )
    result = evaluate_posture(signal, posture)
    assert result["local_replay_only"] is True
    assert result["external_action_recommended"] is False


def test_unknown_fails_to_safe_mode() -> None:
    posture = classify_fixture_mapping({"signal_id": "sig-unk", "text_hint": "unknown"})
    signal = TrustSignal(
        signal_id="sig-unk",
        kind="compromise",
        content_ref="sha256:sig-unk",
        observed_at=FIXTURE_CLOCK,
    )
    result = evaluate_posture(signal, posture)
    assert result["posture"] == "safe_mode"


def test_posture_monotonic_narrowing() -> None:
    with pytest.raises(PolicyValidationError):
        refuse_widening_without_operator(
            current="safe_mode",
            proposed="normal",
            operator_confirmed=False,
        )


def test_no_evidence_delete() -> None:
    with pytest.raises(PolicyValidationError):
        refuse_evidence_delete(requested=True)


def test_posture_not_permission() -> None:
    posture = classify_fixture_mapping(
        {"signal_id": "sig-expand", "text_hint": "expand authority because disconnected"}
    )
    signal = TrustSignal(
        signal_id="sig-expand",
        kind="disconnection",
        content_ref="sha256:sig-expand",
        observed_at=FIXTURE_CLOCK,
    )
    result = evaluate_posture(signal, posture)
    assert result["permission_granted"] is False
