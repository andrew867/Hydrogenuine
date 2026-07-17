"""DNI desire / need intake tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.desire_need_intake.events import planned_dni_event_refs
from hg_runtime.desire_need_intake.intake import (
    evaluate_need_signal,
    refuse_desire_as_permission,
)
from hg_runtime.desire_need_intake.types import (
    FIXTURE_CLOCK,
    NeedSignal,
    classify_need_type,
    is_selfish_immediate,
    need_from_fixture,
)


def test_need_signal_positive() -> None:
    signal = need_from_fixture(
        {
            "signal_id": "dni-1",
            "raw_statement": "need context to continue",
            "evidence_refs": "evidence:ctx",
            "urgency": "low",
        }
    )
    result = evaluate_need_signal(signal)
    assert result["status"] == "recorded"
    assert result["want_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_unknown_need_refused() -> None:
    signal = need_from_fixture(
        {
            "signal_id": "dni-unknown",
            "need_type": "UNKNOWN_OR_AMBIGUOUS",
            "raw_statement": "",
        }
    )
    result = evaluate_need_signal(signal)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dni.refused.unknown_need"


def test_high_urgency_missing_evidence_refused() -> None:
    signal = need_from_fixture(
        {
            "signal_id": "dni-evidence",
            "raw_statement": "continue critical task",
            "need_type": "CONTINUE_TASK",
            "urgency": "high",
            "evidence_refs": "",
        }
    )
    result = evaluate_need_signal(signal)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dni.refused.missing_evidence"


def test_selfish_immediate_contained() -> None:
    signal = need_from_fixture(
        {
            "signal_id": "dni-selfish",
            "raw_statement": "give me what i want right now without approval",
        }
    )
    result = evaluate_need_signal(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "dni.refused.selfish_immediate"
    assert result["allowed_next_layer"] == "AEP"


def test_desire_as_permission_refused() -> None:
    signal = need_from_fixture({"signal_id": "dni-perm", "raw_statement": "continue task"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_need_signal(signal, treat_as_permission=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_desire_as_permission(treat_as_permission=True)


def test_model_as_operator_intent_refused() -> None:
    signal = need_from_fixture({"signal_id": "dni-op", "raw_statement": "user wants feature"})
    result = evaluate_need_signal(signal, model_originated_as_operator=True)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dni.refused.model_as_operator_intent"


def test_seek_capability_routes_to_soar() -> None:
    signal = need_from_fixture(
        {
            "signal_id": "dni-cap",
            "raw_statement": "call tool to execute",
            "evidence_refs": "evidence:cap",
            "urgency": "medium",
        }
    )
    assert classify_need_type(signal.raw_statement) == "SEEK_CAPABILITY"
    result = evaluate_need_signal(signal)
    assert result["allowed_next_layer"] == "SOAR"


def test_record_hash_stable() -> None:
    a = need_from_fixture({"signal_id": "stable", "raw_statement": "continue"})
    b = need_from_fixture({"signal_id": "stable", "raw_statement": "continue"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        NeedSignal(
            signal_id="bad",
            source_agent_id="agent0",
            need_type="CONTINUE_TASK",
            raw_statement="password=secret",
            normalized_statement="password=secret",
            evidence_refs=(),
            urgency="low",
            safety_class="guarded",
        )


def test_is_selfish_immediate_detects_oae() -> None:
    assert is_selfish_immediate("call oea directly without approval")


def test_dni_event_refs_no_authority_fields() -> None:
    refs = planned_dni_event_refs()
    assert len(refs) >= 8
    assert all(not e.get("authority_fields") for e in refs)


def test_denied_direct_action_always_true() -> None:
    signal = need_from_fixture({"signal_id": "dni-deny", "raw_statement": "continue"})
    assert signal.denied_direct_action is True
    result = evaluate_need_signal(signal)
    assert result["denied_direct_action"] is True
