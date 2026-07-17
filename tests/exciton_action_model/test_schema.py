"""Tests for EXCITON action model schema and hashing."""

from __future__ import annotations

import pytest

from hg_runtime.exciton_action_model import (
    AgentActionRequest,
    AgentActionRiskClass,
    AgentActionStatus,
    AgentActionType,
    FIXTURE_UTC,
    action_hash,
    classify_action_risk,
    new_action_id,
    roundtrip_request,
    validate_action_request,
    validate_no_authority_conversion,
)
from hg_runtime.exciton_action_model.adapters import _base_request
from hg_runtime.exciton_action_model.validation import default_surface_for_action


def _sample_request(**kwargs) -> AgentActionRequest:
    action_type = kwargs.pop("action_type", AgentActionType.STATUS_REFRESH)
    req = AgentActionRequest(
        action_id=kwargs.pop("action_id", new_action_id()),
        action_type=action_type,
        source_agent=kwargs.pop("source_agent", "agent0"),
        source_task=kwargs.pop("source_task", "task-1"),
        created_at=kwargs.pop("created_at", FIXTURE_UTC),
        priority=kwargs.pop("priority", 0),
        status=kwargs.pop("status", AgentActionStatus.QUEUED),
        title=kwargs.pop("title", "Test"),
        human_summary=kwargs.pop("human_summary", "Human-readable summary"),
        sanitized_preview=kwargs.pop("sanitized_preview", "Safe preview text"),
        requested_surface=kwargs.pop("requested_surface", default_surface_for_action(action_type)),
        risk_class=kwargs.pop("risk_class", classify_action_risk(action_type)),
        **kwargs,
    )
    req.item_hash = req.to_payload()["item_hash"]
    return req


def test_action_request_schema_validates():
    req = _sample_request()
    assert not validate_action_request(req)
    payload = req.to_payload()
    assert payload["schema"] == "agent-action-request"
    assert payload["item_hash"].startswith("sha256:")


def test_required_fields_enforced():
    req = _sample_request(human_summary="")
    req.item_hash = req.to_payload()["item_hash"]
    errors = validate_action_request(req)
    assert any("human_summary" in e for e in errors)


def test_stable_hash_deterministic():
    req = _sample_request(action_id="act-fixed123456")
    h1 = req.to_payload()["item_hash"]
    h2 = req.to_payload()["item_hash"]
    assert h1 == h2


def test_receipt_hash_deterministic():
    from hg_runtime.exciton_action_model import AgentActionDecisionKind, AgentActionReceipt

    rec = AgentActionReceipt(
        receipt_id="arec-fixed123456",
        action_id="act-fixed123456",
        action_type=AgentActionType.STATUS_REFRESH,
        decision=AgentActionDecisionKind.ALLOW_READ_ONLY,
        reason="test",
        created_at=FIXTURE_UTC,
    )
    p1 = rec.to_payload()
    p2 = rec.to_payload()
    assert p1["receipt_hash"] == p2["receipt_hash"]


def test_no_authority_created_allowed():
    req = _sample_request()
    payload = req.to_payload()
    assert payload["authority_created"] is False
    assert validate_no_authority_conversion({"authority_created": True, "advisory_only": True})


def test_no_permission_granted_allowed():
    req = _sample_request()
    payload = req.to_payload()
    assert payload["permission_granted"] is False


def test_unknown_risk_blocks():
    req = _sample_request(risk_class=AgentActionRiskClass.UNKNOWN)
    errors = validate_action_request(req)
    assert any("unknown risk" in e for e in errors)


def test_roundtrip_preserves_hash():
    req = _sample_request()
    rt = roundtrip_request(req)
    assert rt.item_hash == req.item_hash


@pytest.mark.parametrize("action_type", list(AgentActionType))
def test_all_action_types_constructable(action_type: AgentActionType):
    req = _base_request(action_type)
    assert req.action_type == action_type
    assert req.item_hash
