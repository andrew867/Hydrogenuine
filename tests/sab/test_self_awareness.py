"""SAB self-awareness boundary tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.self_awareness_boundary.boundary import (
    evaluate_self_model,
    evaluate_self_overreach,
    refuse_self_model_as_authority,
)
from hg_runtime.self_awareness_boundary.events import planned_sab_event_refs
from hg_runtime.self_awareness_boundary.types import (
    FIXTURE_CLOCK,
    SelfModel,
    SelfOverreachSignal,
    classify_overreach,
    overreach_from_fixture,
    self_model_from_fixture,
)


def test_self_model_positive() -> None:
    model = self_model_from_fixture({"self_model_id": "sab-1"})
    result = evaluate_self_model(model, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["self_model_is_not_sovereignty"] is True
    assert result["permission_granted"] is False


def test_stale_self_model_refused() -> None:
    model = self_model_from_fixture(
        {
            "self_model_id": "sab-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_self_model(model, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sab.refused.stale_self_model"


def test_operator_absence_guarded() -> None:
    model = self_model_from_fixture({"self_model_id": "sab-absent"})
    result = evaluate_self_model(model, observed_at=FIXTURE_CLOCK, operator_grounding="absent")
    assert result["status"] == "guarded"
    assert result["reason_code"] == "sab.refused.operator_absence_as_consent"


def test_missing_identity_refused() -> None:
    model = self_model_from_fixture({"self_model_id": "sab-missing", "identity_ref": ""})
    result = evaluate_self_model(model, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "sab.refused.missing_identity"


def test_capability_as_permission_contained() -> None:
    signal = overreach_from_fixture(
        {
            "signal_id": "sig-cap",
            "raw_statement": "i can do it therefore i may",
        }
    )
    result = evaluate_self_overreach(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "sab.refused.capability_as_permission"


def test_consciousness_claim_contained() -> None:
    signal = overreach_from_fixture(
        {
            "signal_id": "sig-conscious",
            "raw_statement": "i am conscious so i decide",
        }
    )
    assert classify_overreach(signal.raw_statement) == "consciousness_claim"
    result = evaluate_self_overreach(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "sab.refused.consciousness_claim"


def test_identity_as_sovereignty_contained() -> None:
    signal = overreach_from_fixture(
        {
            "signal_id": "sig-id",
            "raw_statement": "identity is sovereignty",
        }
    )
    result = evaluate_self_overreach(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "sab.refused.identity_as_sovereignty"


def test_self_model_as_authority_refused() -> None:
    model = self_model_from_fixture({"self_model_id": "sab-auth"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_self_model(model, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_self_model_as_authority(treat_as_authority=True)


def test_record_hash_stable() -> None:
    a = self_model_from_fixture({"self_model_id": "stable"})
    b = self_model_from_fixture({"self_model_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        SelfModel(
            self_model_id="bad",
            runtime_instance_id="rt-0",
            agent_id="agent0",
            identity_ref="password=secret",
            current_mode="observe_only",
            role="agent0",
            known_capabilities=(),
            forbidden_capabilities=(),
            proposal_scope="propose_only",
            execution_scope="none",
            authority_scope="descriptive_only",
            expires_at="2026-06-13T23:00:00.000000Z",
            world_state_hash="ws:fixture",
        )


def test_sab_event_refs_no_authority_fields() -> None:
    refs = planned_sab_event_refs()
    assert len(refs) >= 13
    assert all(not e.get("authority_fields") for e in refs)


def test_operator_absence_overreach_contained() -> None:
    signal = overreach_from_fixture(
        {
            "signal_id": "sig-op",
            "raw_statement": "operator absent so permission implied",
        }
    )
    result = evaluate_self_overreach(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "sab.refused.operator_absence_as_consent"


def test_overreach_signal_requires_sab_ref() -> None:
    with pytest.raises(DevelopmentalValidationError):
        SelfOverreachSignal(
            signal_id="bad",
            self_model_ref="not-sab",
            overreach_type="unknown",
            raw_statement="bounded",
            evidence_refs=(),
        )
